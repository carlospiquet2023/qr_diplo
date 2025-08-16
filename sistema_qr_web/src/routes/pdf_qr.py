# ====================================================================
# SISTEMA DE QR CODE PARA PDFs - MÓDULO DE ROTAS PRINCIPAL
# ====================================================================
# Este módulo contém todas as funcionalidades para:
# 1. Processamento de documentos PDF
# 2. Extração e inserção de códigos QR
# 3. Matching inteligente entre alunos e QRs
# 4. Processamento em lote com posicionamento unificado
# ====================================================================

from flask import Blueprint, request, jsonify, send_file
import fitz  # PyMuPDF - Manipulação de documentos PDF
from PIL import Image  # Processamento de imagens
import cv2  # OpenCV - Detecção de QR codes
import numpy as np  # Operações matemáticas
import io
import os
import zipfile
import tempfile
import base64
import re
import unicodedata
from werkzeug.utils import secure_filename

# Blueprint para organizar as rotas do sistema
pdf_qr_bp = Blueprint('pdf_qr', __name__)

# ====================================================================
# SEÇÃO 1: FUNÇÕES DE NORMALIZAÇÃO E LIMPEZA DE NOMES
# ====================================================================
# Estas funções são responsáveis por processar nomes de alunos
# extraídos de PDFs e nomes de arquivos para permitir matching
# inteligente mesmo com pequenas diferenças de formatação.

def limpar_nome_arquivo(nome):
    """
    Limpa e padroniza nomes de arquivos removendo acentos e caracteres especiais.
    
    Funcionalidades:
    - Remove quebras de linha e espaços extras
    - Normaliza acentos (á → a, ç → c, etc.)
    - Remove caracteres especiais mantendo letras, números e espaços
    - Remove extensão .pdf se presente
    
    Args:
        nome (str): Nome original do arquivo ou texto
        
    Returns:
        str: Nome limpo e padronizado
        
    Exemplo:
        "José da Silva.pdf" → "Jose da Silva"
        "María_López" → "Maria Lopez"
    """
    if not nome:
        return ""
    
    # Remove quebras de linha e espaços extras
    nome = re.sub(r'\s+', ' ', nome.strip())
    
    # Normaliza acentos (NFD = separa caracteres e acentos)
    nome_normalizado = unicodedata.normalize('NFD', nome)
    
    # Remove apenas os acentos, mantendo letras
    nome_sem_acento = ''.join(char for char in nome_normalizado if unicodedata.category(char) != 'Mn')
    
    # Remove caracteres especiais, mas mantém letras, números e espaços
    nome_limpo = re.sub(r'[^\w\s]', '', nome_sem_acento)
    
    # Substitui múltiplos espaços por um único espaço
    nome_limpo = re.sub(r'\s+', ' ', nome_limpo)
    
    # Remove .pdf se existir
    if nome_limpo.lower().endswith('.pdf'):
        nome_limpo = nome_limpo[:-4]
    
    return nome_limpo.strip()

def normalizar_para_matching(nome):
    """
    Prepara nomes para matching inteligente com múltiplas variações.
    
    Funcionalidades:
    - Aplica limpeza básica de caracteres
    - Substitui underscores por espaços
    - Converte para minúsculas
    - Cria versão sem espaços para matching flexível
    
    Args:
        nome (str): Nome a ser normalizado
        
    Returns:
        tuple: (nome_com_espacos, nome_sem_espacos) para matching
        
    Exemplo:
        "João_Silva" → ("joao silva", "joaosilva")
        "Ana Costa" → ("ana costa", "anacosta")
    """
    if not nome:
        return ""
    
    # Aplica limpeza básica
    nome_limpo = limpar_nome_arquivo(nome)
    
    # Remove underscores e substitui por espaços
    nome_limpo = nome_limpo.replace('_', ' ')
    
    # Converte para minúsculas para matching case-insensitive
    nome_limpo = nome_limpo.lower()
    
    # Remove espaços para matching mais flexível
    nome_sem_espacos = nome_limpo.replace(' ', '')
    
    return nome_limpo, nome_sem_espacos

# ====================================================================
# SEÇÃO 2: EXTRAÇÃO DE NOMES DE DOCUMENTOS PDF
# ====================================================================
# Esta função extrai automaticamente o nome do aluno de documentos
# PDF usando padrões específicos de diplomas e certificados.

def extrair_nome_do_pdf(pdf_bytes):
    """
    Extrai inteligentemente o nome do aluno de documentos PDF.
    
    Estratégias de extração (em ordem de prioridade):
    1. Padrões específicos de diplomas ("Aluno:", "Certificamos que", etc.)
    2. Detecção automática de nomes próprios no texto
    3. Filtragem de palavras comuns de diplomas
    
    Args:
        pdf_bytes (bytes): Conteúdo binário do arquivo PDF
        
    Returns:
        str or None: Nome do aluno extraído ou None se não encontrado
        
    Padrões reconhecidos:
        - "Aluno: João Silva"
        - "Certificamos que Maria Santos"
        - "Nome: Ana Costa"
        - "Formando: Carlos Oliveira"
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        text = page.get_text()
        doc.close()
        
        print(f"Texto extraído do PDF:\n{text}")
        
        # ESTRATÉGIA 1: Padrões específicos para diplomas/certificados
        patterns = [
            r'Aluno:\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*)',
            r'Nome do aluno:\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*)',
            r'Certificamos que\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*)',
            r'Nome:\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*)',
            r'Formando:\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*)',
            r'Graduando:\s*([A-ZÀ-Ú][a-zà-ú]+(?:\s[A-ZÀ-Ú][a-zà-ú]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                # Remove quebras de linha e espaços extras
                nome = re.sub(r'\s+', ' ', nome)
                # Remove texto adicional após o nome (como curso, etc.)
                nome = re.split(r'\n|Curso:|curso:|Curso\s|curso\s', nome)[0].strip()
                # Remove palavras que não fazem parte do nome
                palavras = nome.split()
                nome_limpo_palavras = []
                for palavra in palavras:
                    palavra_lower = palavra.lower()
                    if palavra_lower not in ['curso', 'de', 'graduação', 'pós', 'especialização']:
                        nome_limpo_palavras.append(palavra)
                    else:
                        break  # Para quando encontrar uma palavra que não é nome
                
                nome_final = ' '.join(nome_limpo_palavras)
                nome_limpo = limpar_nome_arquivo(nome_final)
                print(f"Nome extraído por padrão '{pattern}': '{nome}' -> '{nome_limpo}'")
                return nome_limpo
        
        # ESTRATÉGIA 2: Detecção automática de nomes próprios
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Ignora linhas muito curtas ou muito longas
            if len(line) < 5 or len(line) > 80:
                continue
            
            # Procura por padrão de nome (palavras com primeira letra maiúscula)
            words = line.split()
            if len(words) >= 2 and len(words) <= 6:  # Nome típico tem 2-6 palavras
                # Verifica se todas as palavras começam com maiúscula (exceto conectores)
                conectores = ['de', 'da', 'do', 'dos', 'das', 'e', 'del', 'van', 'von']
                nome_valido = True
                for word in words:
                    if word.lower() not in conectores and (len(word) < 2 or not word[0].isupper()):
                        nome_valido = False
                        break
                
                if nome_valido:
                    # Verifica se não contém números ou símbolos estranhos
                    if not re.search(r'[0-9@#$%^&*()_+={}|\\:";\'<>?,.\/]', line):
                        # ESTRATÉGIA 3: Filtra palavras comuns de diplomas
                        palavras_ignorar = ['diploma', 'certificado', 'curso', 'universidade', 
                                          'faculdade', 'instituto', 'graduação', 'bacharelado',
                                          'licenciatura', 'tecnólogo', 'especialização', 'mestrado',
                                          'doutorado', 'pós-graduação', 'conclusão', 'formatura',
                                          'deliberação', 'credenciamento', 'parecer', 'renovação',
                                          'data', 'impressão', 'página', 'documento']
                        
                        if not any(palavra in line.lower() for palavra in palavras_ignorar):
                            nome_limpo = limpar_nome_arquivo(line)
                            print(f"Nome extraído por detecção automática: '{line}' -> '{nome_limpo}'")
                            return nome_limpo
        
        print("Nenhum nome encontrado no PDF")
        return None
    except Exception as e:
        print(f"Erro ao extrair nome do PDF: {e}")
        return None

# ====================================================================
# SEÇÃO 3: DETECÇÃO DE QR CODES EM IMAGENS
# ====================================================================
# Esta função utiliza OpenCV para detectar automaticamente a posição
# de códigos QR em imagens, essencial para extração de QRs existentes.

def detectar_qr_code_na_imagem(img_array):
    """
    Detecta automaticamente a posição e dimensões de QR codes em imagens.
    
    Funcionalidades:
    - Converte imagem para escala de cinza
    - Utiliza detector OpenCV com múltiplas estratégias
    - Aplica threshold adaptivo quando necessário
    - Adiciona margem de segurança ao QR detectado
    
    Args:
        img_array (numpy.ndarray): Array da imagem em formato RGB
        
    Returns:
        tuple or None: (x, y, width, height) do QR ou None se não encontrado
        
    Estratégias de detecção:
    1. Detecção direta na imagem original
    2. Aplicação de threshold adaptivo para melhorar contraste
    """
    try:
        # Converte para escala de cinza se necessário
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # ESTRATÉGIA 1: Detecção direta
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(gray)
        
        if points is not None and len(points) > 0:
            points = points[0]
            x = int(min(points[:, 0]))
            y = int(min(points[:, 1]))
            w = int(max(points[:, 0]) - x)
            h = int(max(points[:, 1]) - y)
            # Adiciona margem de segurança
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(img_array.shape[1] - x, w + 2 * margin)
            h = min(img_array.shape[0] - y, h + 2 * margin)
            print(f"QR Code detectado em: x={x}, y={y}, w={w}, h={h}")
            return (x, y, w, h)
        
        # ESTRATÉGIA 2: Threshold adaptivo para melhorar contraste
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        data, points, _ = detector.detectAndDecode(thresh)
        
        if points is not None and len(points) > 0:
            points = points[0]
            x = int(min(points[:, 0]))
            y = int(min(points[:, 1]))
            w = int(max(points[:, 0]) - x)
            h = int(max(points[:, 1]) - y)
            # Adiciona margem de segurança
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(img_array.shape[1] - x, w + 2 * margin)
            h = min(img_array.shape[0] - y, h + 2 * margin)
            print(f"QR Code detectado com threshold em: x={x}, y={y}, w={w}, h={h}")
            return (x, y, w, h)
            
        print("Nenhum QR Code detectado na imagem")
        
    except Exception as e:
        print(f"Erro na detecção do QR code: {e}")
    return None

# ====================================================================
# SEÇÃO 4: ENDPOINTS DA API - UPLOAD E RENDERIZAÇÃO DE PDFs
# ====================================================================
# Estes endpoints lidam com o carregamento e exibição de documentos PDF.

@pdf_qr_bp.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """
    Endpoint para upload de PDF e renderização de páginas para visualização.
    
    Funcionalidades:
    - Recebe arquivo PDF via multipart/form-data
    - Renderiza todas as páginas como imagens PNG
    - Retorna dados base64 para exibição no frontend
    - Inclui metadados de dimensões reais e renderizadas
    
    Returns:
        JSON: {
            'success': bool,
            'total_pages': int,
            'pages': [{'page_num', 'image', 'width', 'height', 'display_width', 'display_height'}],
            'filename': str
        }
        
    Escalas utilizadas:
        - Matrix(1.5, 1.5): Boa qualidade para visualização web
        - Preserva proporções originais do documento
    """
    try:
        if 'pdf' not in request.files:
            return jsonify({'error': 'Nenhum arquivo PDF enviado'}), 400
        
        pdf_file = request.files['pdf']
        if pdf_file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        pdf_bytes = pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(1.5, 1.5)  # Escala para boa qualidade
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Obtém as dimensões reais da página em pontos
            page_rect = page.rect
            
            pages.append({
                'page_num': page_num,
                'image': f"data:image/png;base64,{img_base64}",
                'width': page_rect.width,    # Largura real em pontos
                'height': page_rect.height,  # Altura real em pontos
                'display_width': pix.width,  # Largura da imagem renderizada
                'display_height': pix.height # Altura da imagem renderizada
            })
        
        doc.close()
        
        return jsonify({
            'success': True,
            'total_pages': len(pages),
            'pages': pages,
            'filename': pdf_file.filename
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao processar PDF: {str(e)}'}), 500

# ====================================================================
# SEÇÃO 5: EXTRAÇÃO DE QR CODES DE DOCUMENTOS EXISTENTES
# ====================================================================
# Este endpoint extrai QR codes de PDFs já processados (ex: diplomas assinados).

@pdf_qr_bp.route('/extract-qr', methods=['POST'])
def extract_qr():
    """
    Endpoint para extrair QR codes de múltiplos PDFs existentes.
    
    Processo de extração:
    1. Recebe múltiplos arquivos PDF
    2. Para cada PDF, extrai o nome do aluno
    3. Procura QR codes em todas as páginas
    4. Retorna QRs extraídos associados aos nomes
    
    Funcionalidades:
    - Processamento em lote de múltiplos PDFs
    - Extração automática de nomes de alunos
    - Detecção de QR codes com alta resolução (Matrix 3.0)
    - Log detalhado do processamento
    
    Returns:
        JSON: {
            'success': bool,
            'extracted_qrs': [{'nome_aluno', 'filename', 'image', 'page_num', 'original_pdf'}],
            'total_extracted': int,
            'processing_log': [str]
        }
        
    Resolução de extração:
        - Matrix(3.0, 3.0): Alta resolução para melhor detecção de QRs
    """
    try:
        if 'pdfs' not in request.files:
            return jsonify({'error': 'Nenhum arquivo PDF enviado'}), 400
        
        pdf_files = request.files.getlist('pdfs')
        extracted_qrs = []
        processing_log = []
        
        for pdf_file in pdf_files:
            if pdf_file.filename == '':
                continue
            
            print(f"Processando arquivo: {pdf_file.filename}")
            processing_log.append(f"Processando: {pdf_file.filename}")
            
            pdf_bytes = pdf_file.read()
            nome_aluno = extrair_nome_do_pdf(pdf_bytes)
            
            if not nome_aluno:
                msg = f"Nome não encontrado em {pdf_file.filename}"
                print(msg)
                processing_log.append(msg)
                continue
            
            print(f"Nome extraído: {nome_aluno}")
            processing_log.append(f"Nome encontrado: {nome_aluno}")
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            qr_found = False
            
            # Procura QR em todas as páginas do documento
            for page_num in range(len(doc)):
                print(f"Analisando página {page_num + 1} de {len(doc)}")
                page = doc[page_num]
                
                # Aumenta a resolução para melhor detecção
                mat = fitz.Matrix(3.0, 3.0)
                pix = page.get_pixmap(matrix=mat)
                
                # Converte para numpy array
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                img_array = np.array(img)
                
                qr_coords = detectar_qr_code_na_imagem(img_array)
                if qr_coords:
                    x, y, w, h = qr_coords
                    qr_img = img.crop((x, y, x + w, y + h))
                    
                    # Converte para base64
                    buffer = io.BytesIO()
                    qr_img.save(buffer, format='PNG')
                    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    extracted_qrs.append({
                        'nome_aluno': nome_aluno,
                        'filename': f"{nome_aluno}.png",
                        'image': f"data:image/png;base64,{qr_base64}",
                        'page_num': page_num + 1,
                        'original_pdf': pdf_file.filename
                    })
                    
                    msg = f"QR extraído de {pdf_file.filename} página {page_num + 1}"
                    print(msg)
                    processing_log.append(msg)
                    qr_found = True
                    break
            
            if not qr_found:
                msg = f"Nenhum QR encontrado em {pdf_file.filename}"
                print(msg)
                processing_log.append(msg)
            
            doc.close()
        
        return jsonify({
            'success': True,
            'extracted_qrs': extracted_qrs,
            'total_extracted': len(extracted_qrs),
            'processing_log': processing_log
        })
        
    except Exception as e:
        error_msg = f'Erro ao extrair QR codes: {str(e)}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500

# ====================================================================
# SEÇÃO 6: INSERÇÃO DE QR CODES EM DOCUMENTOS
# ====================================================================
# Este endpoint insere QR codes em PDFs em posições específicas.

@pdf_qr_bp.route('/insert-qr', methods=['POST'])
def insert_qr():
    """
    Endpoint para inserir QR codes em posições específicas de PDFs.
    
    Funcionalidades:
    - Recebe PDF e QR em formato base64
    - Suporta múltiplas posições por página
    - Converte coordenadas de tela para coordenadas PDF
    - Redimensiona QRs automaticamente
    - Garante que QRs fiquem dentro dos limites da página
    
    Entrada JSON:
        {
            'pdf_base64': str,
            'qr_base64': str,
            'qr_positions': [{'page', 'x', 'y', 'size', 'canvas_width', 'canvas_height'}]
        }
        
    Returns:
        JSON: {'success': bool, 'pdf_base64': str}
        
    Sistema de coordenadas:
        - Converte coordenadas de interface para coordenadas PDF reais
        - Mantém proporções e garante limites da página
    """
    try:
        data = request.get_json()
        
        if not data or 'pdf_base64' not in data or 'qr_base64' not in data:
            return jsonify({'error': 'Dados incompletos'}), 400
        
        # Decodifica PDF
        pdf_data = base64.b64decode(data['pdf_base64'].split(',')[1])
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        # Decodifica QR
        qr_data = base64.b64decode(data['qr_base64'].split(',')[1])
        qr_image = Image.open(io.BytesIO(qr_data))
        
        # Processa posições dos QR codes
        qr_positions = data.get('qr_positions', [])
        
        # Processa cada posição de QR solicitada
        for position in qr_positions:
            page_num = position['page']
            x = position['x']
            y = position['y']
            size = position['size']
            
            if page_num < len(doc):
                page = doc[page_num]
                page_rect = page.rect
                
                # SISTEMA DE COORDENADAS: Compatibilidade com diferentes sistemas
                if 'real_width' in position and 'real_height' in position:
                    # Coordenadas já são reais (sistema novo), usa diretamente
                    pdf_x = x
                    pdf_y = y
                    pdf_size = size
                else:
                    # Sistema legado - converte coordenadas da tela para coordenadas do PDF
                    scale_x = page_rect.width / position['canvas_width']
                    scale_y = page_rect.height / position['canvas_height']
                    
                    pdf_x = x * scale_x
                    pdf_y = y * scale_y
                    pdf_size = size * min(scale_x, scale_y)
                
                # VALIDAÇÃO: Garante que o QR fique dentro dos limites da página
                pdf_x = max(0, min(pdf_x, page_rect.width - pdf_size))
                pdf_y = max(0, min(pdf_y, page_rect.height - pdf_size))
                
                # Redimensiona QR mantendo qualidade
                qr_resized = qr_image.resize((int(pdf_size), int(pdf_size)), Image.Resampling.LANCZOS)
                
                # Converte para bytes e insere no PDF
                qr_bytes = io.BytesIO()
                qr_resized.save(qr_bytes, format='PNG')
                qr_bytes.seek(0)
                
                rect = fitz.Rect(pdf_x, pdf_y, pdf_x + pdf_size, pdf_y + pdf_size)
                page.insert_image(rect, stream=qr_bytes.getvalue())
        
        # Salva PDF modificado em memória
        output_buffer = io.BytesIO()
        doc.save(output_buffer)
        doc.close()
        
        output_buffer.seek(0)
        pdf_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'pdf_base64': f"data:application/pdf;base64,{pdf_base64}"
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao inserir QR code: {str(e)}'}), 500

# ====================================================================
# SEÇÃO 7: PROCESSAMENTO EM LOTE COM MATCHING INTELIGENTE
# ====================================================================
# Este é o endpoint principal para processamento em lote, associando
# cada QR ao seu respectivo aluno através de matching inteligente.

@pdf_qr_bp.route('/batch-process', methods=['POST'])
def batch_process():
    """
    Processa múltiplos PDFs em lote associando QR codes individuais por aluno.
    
    FUNCIONALIDADE PRINCIPAL:
    - Cada aluno recebe SEU PRÓPRIO QR code (não o mesmo para todos)
    - Posicionamento unificado (todos os QRs na mesma posição)
    - Matching inteligente por nome (PDF ↔ QR)
    
    PROCESSO:
    1. Mapeia QRs extraídos por nome do arquivo
    2. Para cada diploma (PDF):
       a. Extrai nome do aluno
       b. Encontra QR correspondente
       c. Insere na posição unificada
    3. Retorna todos os PDFs processados
    
    ENTRADA:
        - pdfs: Lista de arquivos PDF (diplomas)
        - qrs: Lista de arquivos PNG (QRs extraídos)  
        - qr_position: JSON com posição unificada {x, y, size}
        
    SAÍDA:
        - processed_pdfs: Lista de PDFs com QRs inseridos
        - processing_log: Log detalhado do processamento
        - total_processed: Contador de sucessos
        
    MATCHING INTELIGENTE:
        - "Maria_Silva.pdf" ↔ "Maria Silva.png"
        - "joao-santos.pdf" ↔ "João Santos.png"
        - Remove acentos, ignora case, trata separadores
    """
    try:
        # VALIDAÇÃO DOS DADOS DE ENTRADA
        if 'pdfs' not in request.files or 'qrs' not in request.files:
            return jsonify({'error': 'Diplomas (PDFs) e QRs extraídos são necessários'}), 400
        
        if 'qr_position' not in request.form:
            return jsonify({'error': 'A posição do QR Code é necessária'}), 400

        diploma_files = request.files.getlist('pdfs')  # PDFs dos diplomas
        qr_files = request.files.getlist('qrs')        # PNGs dos QRs extraídos
        qr_position_str = request.form['qr_position']
        
        import json
        qr_position = json.loads(qr_position_str)
        
        processing_log = []
        log_msg = "🚀 Iniciando processamento em lote com posição unificada..."
        print(log_msg)
        processing_log.append(log_msg)

        # ETAPA 1: MAPEAMENTO DE QRs POR NOME
        # Cria um dicionário que associa nomes normalizados aos bytes dos QRs
        qr_map = {}
        for qr_file in qr_files:
            qr_filename = qr_file.filename
            if qr_filename.lower().endswith('.png'):
                # Remove extensão .png e normaliza o nome
                nome_qr = os.path.splitext(qr_filename)[0]
                nome_normalizado, nome_sem_espacos = normalizar_para_matching(nome_qr)
                
                # Lê os bytes da imagem QR
                qr_bytes = qr_file.read()
                
                # Mapeia por ambas as versões do nome para matching flexível
                qr_map[nome_normalizado] = qr_bytes
                qr_map[nome_sem_espacos] = qr_bytes
                
                log_msg = f"✅ QR '{qr_filename}' mapeado para '{nome_qr}'"
                print(log_msg)
                processing_log.append(log_msg)

        # ETAPA 2: PROCESSAMENTO DE CADA DIPLOMA
        processed_pdfs = []
        success_count = 0
        
        for diploma_file in diploma_files:
            original_filename = secure_filename(diploma_file.filename)
            log_msg = f"📄 Processando diploma: {original_filename}"
            print(log_msg)
            processing_log.append(log_msg)
            
            diploma_bytes = diploma_file.read()
            
            try:
                # ETAPA 2A: EXTRAÇÃO DO NOME DO ALUNO
                nome_aluno_diploma = extrair_nome_do_pdf(diploma_bytes)
                if not nome_aluno_diploma:
                    # Fallback: usa o nome do arquivo se não conseguir extrair do PDF
                    nome_arquivo = os.path.splitext(original_filename)[0]
                    nome_aluno_diploma = limpar_nome_arquivo(nome_arquivo)
                    log_msg = f"📝 Nome extraído do arquivo: '{nome_aluno_diploma}'"
                else:
                    log_msg = f"📝 Nome extraído do PDF: '{nome_aluno_diploma}'"
                
                print(log_msg)
                processing_log.append(log_msg)
                
                # Normaliza nome do diploma para matching
                nome_normalizado_diploma, nome_sem_espacos_diploma = normalizar_para_matching(nome_aluno_diploma)

                # ETAPA 2B: BUSCA DO QR CORRESPONDENTE
                # Tenta encontrar o QR usando as duas versões normalizadas do nome
                matched_qr_bytes = qr_map.get(nome_normalizado_diploma) or qr_map.get(nome_sem_espacos_diploma)

                if not matched_qr_bytes:
                    log_msg = f"❌ ERRO: QR para '{nome_aluno_diploma}' não encontrado"
                    print(log_msg)
                    processing_log.append(log_msg)
                    continue
                
                # ETAPA 2C: INSERÇÃO DO QR NA POSIÇÃO UNIFICADA
                doc = fitz.open(stream=diploma_bytes, filetype="pdf")
                if len(doc) > 0:
                    page = doc[0]  # Sempre insere na primeira página
                    x, y, size = qr_position['x'], qr_position['y'], qr_position['size']
                    page_rect = page.rect
                    
                    # Validação: Garante que o QR fique dentro dos limites da página
                    pdf_x = max(0, min(x, page_rect.width - size))
                    pdf_y = max(0, min(y, page_rect.height - size))
                    
                    # Insere o QR individual do aluno na posição unificada
                    rect = fitz.Rect(pdf_x, pdf_y, pdf_x + size, pdf_y + size)
                    page.insert_image(rect, stream=matched_qr_bytes)
                    
                    log_msg = f"✅ QR inserido em {original_filename}"
                    print(log_msg)
                    processing_log.append(log_msg)

                # ETAPA 2D: SALVA O PDF PROCESSADO
                output_buffer = io.BytesIO()
                doc.save(output_buffer)
                doc.close()
                
                output_buffer.seek(0)
                pdf_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                
                # Gera nome do arquivo de saída
                base_name, ext = os.path.splitext(original_filename)
                new_filename = f"{base_name}_com_qr{ext}"
                
                processed_pdfs.append({
                    'filename': new_filename,
                    'pdf_base64': f"data:application/pdf;base64,{pdf_base64}"
                })
                
                success_count += 1

            except Exception as e:
                error_msg = f"❌ Erro ao processar '{original_filename}': {str(e)}"
                print(error_msg)
                processing_log.append(error_msg)

        # RESULTADO FINAL
        result_msg = f"🎯 Processamento concluído: {success_count} de {len(diploma_files)} PDFs processados"
        print(result_msg)
        processing_log.append(result_msg)
        
        return jsonify({
            'success': True,
            'processed_pdfs': processed_pdfs,
            'total_processed': success_count,
            'processing_log': processing_log
        })
        
    except Exception as e:
        error_msg = f'❌ Erro geral no processamento em lote: {str(e)}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500

# ====================================================================
# SEÇÃO 8: ENDPOINTS DE SALVAMENTO DE PÁGINAS (FUNCIONALIDADES LEGADAS)
# ====================================================================
# Estes endpoints mantêm compatibilidade com versões anteriores do sistema.

@pdf_qr_bp.route('/save-page', methods=['POST'])
def save_page():
    """
    Salva uma página específica do PDF com QR codes inseridos.
    
    FUNCIONALIDADE LEGADA:
    - Mantida para compatibilidade
    - Processa apenas uma página por vez
    - Permite múltiplas posições de QR na mesma página
    
    PARÂMETROS:
        - pdf: Arquivo PDF
        - qr: Arquivo de imagem QR
        - pageNumber: Número da página (0-indexed)
        - positions: JSON com posições dos QRs
    """
    try:
        # Validação dos parâmetros de entrada
        pdf_file = request.files.get('pdf')
        qr_file = request.files.get('qr')
        page_number = int(request.form.get('pageNumber', 0))
        positions_str = request.form.get('positions', '[]')
        
        if not pdf_file or not qr_file:
            return jsonify({'error': 'PDF e QR Code são obrigatórios'}), 400
        
        positions = eval(positions_str) if positions_str else []
        
        # Carrega e processa o PDF
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        if page_number >= len(pdf_document):
            return jsonify({'error': 'Número da página inválido'}), 400
        
        # Carrega a imagem do QR
        qr_image = Image.open(qr_file).convert('RGBA')
        
        # Processa apenas a página especificada
        page = pdf_document[page_number]
        
        # Insere QRs em todas as posições solicitadas
        for pos in positions:
            x, y = pos['x'], pos['y']
            size = pos.get('size', 50)
            
            # Redimensiona o QR mantendo qualidade
            qr_resized = qr_image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Converte para bytes e insere no PDF
            qr_bytes = io.BytesIO()
            qr_resized.save(qr_bytes, format='PNG')
            qr_bytes = qr_bytes.getvalue()
            
            rect = fitz.Rect(x, y, x + size, y + size)
            page.insert_image(rect, stream=qr_bytes)
        
        # Salva em memória e retorna como download
        output = io.BytesIO()
        pdf_document.save(output)
        pdf_document.close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'diploma_pagina_{page_number + 1}.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro ao salvar página: {str(e)}'}), 500
        output = io.BytesIO()
        pdf_document.save(output)
        pdf_document.close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'diploma_pagina_{page_number + 1}.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro ao salvar página: {str(e)}'}), 500

@pdf_qr_bp.route('/save-all-pages', methods=['POST'])
def save_all_pages():
    """
    Salva todas as páginas do PDF com QR codes inseridos em múltiplas posições.
    
    FUNCIONALIDADE LEGADA:
    - Mantida para compatibilidade
    - Processa múltiplas páginas simultaneamente  
    - Permite diferentes posições de QR por página
    
    PARÂMETROS:
        - pdf: Arquivo PDF
        - qr: Arquivo de imagem QR
        - allPositions: JSON com posições por página
    """
    try:
        # Validação dos parâmetros de entrada
        pdf_file = request.files.get('pdf')
        qr_file = request.files.get('qr')
        all_positions_str = request.form.get('allPositions', '{}')
        
        if not pdf_file or not qr_file:
            return jsonify({'error': 'PDF e QR Code são obrigatórios'}), 400
        
        all_positions = eval(all_positions_str) if all_positions_str else {}
        
        # Carrega e processa o PDF
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        # Carrega a imagem do QR
        qr_image = Image.open(qr_file).convert('RGBA')
        
        # Processa todas as páginas que possuem QRs definidos
        for page_num, positions in all_positions.items():
            if not positions:  # Pula páginas sem QRs
                continue
                
            page_index = int(page_num)
            if page_index >= len(pdf_document):
                continue
                
            page = pdf_document[page_index]
            
            # Insere QRs em todas as posições da página
            for pos in positions:
                x, y = pos['x'], pos['y']
                size = pos.get('size', 50)
                
                # Redimensiona o QR mantendo qualidade
                qr_resized = qr_image.resize((size, size), Image.Resampling.LANCZOS)
                
                # Converte para bytes e insere no PDF
                qr_bytes = io.BytesIO()
                qr_resized.save(qr_bytes, format='PNG')
                qr_bytes = qr_bytes.getvalue()
                
                rect = fitz.Rect(x, y, x + size, y + size)
                page.insert_image(rect, stream=qr_bytes)
        
        # Salva em memória e retorna como download
        output = io.BytesIO()
        pdf_document.save(output)
        pdf_document.close()
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='diploma_completo_com_qrs.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro ao salvar todas as páginas: {str(e)}'}), 500

# ====================================================================
# FIM DO MÓDULO - TODAS AS FUNCIONALIDADES IMPLEMENTADAS
# ====================================================================
# 
# RESUMO DAS FUNCIONALIDADES:
# 
# 1. NORMALIZAÇÃO DE NOMES (Seção 1):
#    - limpar_nome_arquivo(): Remove acentos e caracteres especiais
#    - normalizar_para_matching(): Prepara nomes para matching inteligente
# 
# 2. EXTRAÇÃO DE DADOS (Seções 2-3):
#    - extrair_nome_do_pdf(): Extrai nomes de alunos de documentos
#    - detectar_qr_code_na_imagem(): Detecta QRs em imagens
# 
# 3. ENDPOINTS PRINCIPAIS (Seções 4-7):
#    - /upload-pdf: Upload e renderização de PDFs
#    - /extract-qr: Extração de QRs de documentos existentes
#    - /insert-qr: Inserção de QRs em posições específicas
#    - /batch-process: Processamento em lote com matching inteligente
# 
# 4. ENDPOINTS LEGADOS (Seção 8):
#    - /save-page: Salvamento de páginas individuais
#    - /save-all-pages: Salvamento de múltiplas páginas
# 
# PRINCIPAIS MELHORIAS DA REFATORAÇÃO:
# - Documentação completa de cada bloco funcional
# - Separação clara de responsabilidades
# - Logs com emojis para melhor visualização
# - Comentários explicativos do processo
# - Estrutura modular para fácil manutenção
# - Validações consistentes em todos os endpoints
# ====================================================================
