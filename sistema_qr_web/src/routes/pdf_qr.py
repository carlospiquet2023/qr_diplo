from flask import Blueprint, request, jsonify, send_file
import fitz  # PyMuPDF
from PIL import Image
import cv2
import numpy as np
import io
import os
import zipfile
import tempfile
import base64
import re
import unicodedata
from werkzeug.utils import secure_filename

pdf_qr_bp = Blueprint('pdf_qr', __name__)

def limpar_nome_arquivo(nome):
    """Remove acentos e caracteres especiais do nome do arquivo para matching"""
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
    """Normaliza nome especificamente para matching (mais agressivo)"""
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

def extrair_nome_do_pdf(pdf_bytes):
    """Extrai o nome do aluno do PDF"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        text = page.get_text()
        doc.close()
        
        print(f"Texto extraído do PDF:\n{text}")
        
        # Padrões específicos para diplomas/certificados
        patterns = [
            r'Aluno:\s*(.+)',           # "Aluno: Nome"
            r'Nome do aluno:\s*(.+)',   # "Nome do aluno: Nome"
            r'Aluno\s*:\s*(.+)',        # "Aluno : Nome" (com espaços)
            r'Nome:\s*(.+)',            # "Nome: Nome"
            r'Formando:\s*(.+)',        # "Formando: Nome"
            r'Graduando:\s*(.+)',       # "Graduando: Nome"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                # Remove quebras de linha e espaços extras
                nome = re.sub(r'\s+', ' ', nome)
                # Remove texto adicional após o nome (como curso, etc.)
                nome = re.split(r'\n|Curso:|curso:', nome)[0].strip()
                nome_limpo = limpar_nome_arquivo(nome)
                print(f"Nome extraído por padrão '{pattern}': '{nome}' -> '{nome_limpo}'")
                return nome_limpo
        
        # Se não encontrou com padrões, busca por nomes próprios
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
                        # Verifica se não é uma palavra comum de diploma
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

def detectar_qr_code_na_imagem(img_array):
    """Detecta a posição do QR code na imagem usando OpenCV"""
    try:
        # Converte para escala de cinza se necessário
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Tenta diferentes métodos de detecção
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(gray)
        
        if points is not None and len(points) > 0:
            points = points[0]
            x = int(min(points[:, 0]))
            y = int(min(points[:, 1]))
            w = int(max(points[:, 0]) - x)
            h = int(max(points[:, 1]) - y)
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(img_array.shape[1] - x, w + 2 * margin)
            h = min(img_array.shape[0] - y, h + 2 * margin)
            print(f"QR Code detectado em: x={x}, y={y}, w={w}, h={h}")
            return (x, y, w, h)
        
        # Se não encontrou, tenta com processamento adicional
        # Aplica threshold adaptivo
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        data, points, _ = detector.detectAndDecode(thresh)
        
        if points is not None and len(points) > 0:
            points = points[0]
            x = int(min(points[:, 0]))
            y = int(min(points[:, 1]))
            w = int(max(points[:, 0]) - x)
            h = int(max(points[:, 1]) - y)
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

@pdf_qr_bp.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """Endpoint para upload de PDF e renderização de páginas"""
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

@pdf_qr_bp.route('/extract-qr', methods=['POST'])
def extract_qr():
    """Endpoint para extrair QR codes de PDFs"""
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

@pdf_qr_bp.route('/insert-qr', methods=['POST'])
def insert_qr():
    """Endpoint para inserir QR codes em PDFs"""
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
        
        for position in qr_positions:
            page_num = position['page']
            x = position['x']
            y = position['y']
            size = position['size']
            
            if page_num < len(doc):
                page = doc[page_num]
                page_rect = page.rect
                
                # Se as coordenadas já são reais (novo sistema), usa diretamente
                if 'real_width' in position and 'real_height' in position:
                    # Coordenadas já são reais, usa diretamente
                    pdf_x = x
                    pdf_y = y
                    pdf_size = size
                else:
                    # Sistema antigo - converte coordenadas da tela para coordenadas do PDF
                    scale_x = page_rect.width / position['canvas_width']
                    scale_y = page_rect.height / position['canvas_height']
                    
                    pdf_x = x * scale_x
                    pdf_y = y * scale_y
                    pdf_size = size * min(scale_x, scale_y)
                
                # Garante que o QR fique dentro dos limites da página
                pdf_x = max(0, min(pdf_x, page_rect.width - pdf_size))
                pdf_y = max(0, min(pdf_y, page_rect.height - pdf_size))
                
                # Redimensiona QR
                qr_resized = qr_image.resize((int(pdf_size), int(pdf_size)), Image.Resampling.LANCZOS)
                
                # Converte para bytes
                qr_bytes = io.BytesIO()
                qr_resized.save(qr_bytes, format='PNG')
                qr_bytes.seek(0)
                
                # Insere no PDF
                rect = fitz.Rect(pdf_x, pdf_y, pdf_x + pdf_size, pdf_y + pdf_size)
                page.insert_image(rect, stream=qr_bytes.getvalue())
        
        # Salva PDF modificado
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

@pdf_qr_bp.route('/batch-process', methods=['POST'])
def batch_process():
    """Endpoint para processamento em lote com posição unificada"""
    try:
        if 'pdfs' not in request.files or 'qr' not in request.files:
            return jsonify({'error': 'Arquivos PDF e QR são necessários'}), 400
        
        if 'qr_position' not in request.form:
            return jsonify({'error': 'Posição do QR Code é necessária'}), 400

        pdf_files = request.files.getlist('pdfs')
        qr_file = request.files['qr']
        qr_position_str = request.form['qr_position']
        
        # Desserializa a posição do QR
        import json
        qr_position = json.loads(qr_position_str)
        
        processing_log = []
        print("Iniciando processamento em lote com posição unificada...")
        processing_log.append("Iniciando processamento em lote...")

        # Carrega a imagem do QR
        qr_image = Image.open(qr_file.stream)
        
        processed_pdfs = []
        
        for pdf_file in pdf_files:
            if not pdf_file.filename:
                continue
            
            original_filename = secure_filename(pdf_file.filename)
            print(f"Processando PDF: {original_filename}")
            processing_log.append(f"Processando PDF: {original_filename}")
            
            pdf_bytes = pdf_file.read()
            
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                
                # Insere QR na primeira página usando a posição fornecida
                if len(doc) > 0:
                    page = doc[0]
                    
                    # Pega os dados da posição
                    x = qr_position['x']
                    y = qr_position['y']
                    size = qr_position['size']
                    
                    # Garante que o QR fique dentro dos limites da página
                    page_rect = page.rect
                    pdf_x = max(0, min(x, page_rect.width - size))
                    pdf_y = max(0, min(y, page_rect.height - size))
                    
                    # Redimensiona QR
                    qr_resized = qr_image.resize((int(size), int(size)), Image.Resampling.LANCZOS)
                    
                    # Converte para bytes
                    qr_bytes_io = io.BytesIO()
                    qr_resized.save(qr_bytes_io, format='PNG')
                    qr_bytes_io.seek(0)
                    
                    # Insere no PDF
                    rect = fitz.Rect(pdf_x, pdf_y, pdf_x + size, pdf_y + size)
                    page.insert_image(rect, stream=qr_bytes_io.getvalue())
                    
                    print(f"QR inserido em {original_filename}")
                    processing_log.append(f"QR inserido com sucesso em {original_filename}")

                # Salva PDF processado
                output_buffer = io.BytesIO()
                doc.save(output_buffer)
                doc.close()
                
                output_buffer.seek(0)
                pdf_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                
                # Gera novo nome de arquivo
                base_name, ext = os.path.splitext(original_filename)
                new_filename = f"{base_name}_com_qr{ext}"
                
                processed_pdfs.append({
                    'filename': new_filename,
                    'pdf_base64': f"data:application/pdf;base64,{pdf_base64}"
                })

            except Exception as e:
                error_msg = f"Falha ao processar {original_filename}: {str(e)}"
                print(error_msg)
                processing_log.append(error_msg)

        result_msg = f"Processamento concluído: {len(processed_pdfs)} de {len(pdf_files)} PDFs processados"
        print(result_msg)
        processing_log.append(result_msg)
        
        return jsonify({
            'success': True,
            'processed_pdfs': processed_pdfs,
            'total_processed': len(processed_pdfs),
            'processing_log': processing_log
        })
        
    except Exception as e:
        error_msg = f'Erro no processamento em lote: {str(e)}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500

@pdf_qr_bp.route('/save-page', methods=['POST'])
def save_page():
    """Salva uma página específica do PDF com QR Code inserido"""
    try:
        pdf_file = request.files.get('pdf')
        qr_file = request.files.get('qr')
        page_number = int(request.form.get('pageNumber', 0))
        positions_str = request.form.get('positions', '[]')
        
        if not pdf_file or not qr_file:
            return jsonify({'error': 'PDF e QR Code são obrigatórios'}), 400
        
        positions = eval(positions_str) if positions_str else []
        
        # Abre o PDF
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        if page_number >= len(pdf_document):
            return jsonify({'error': 'Número da página inválido'}), 400
        
        # Carrega a imagem do QR
        qr_image = Image.open(qr_file).convert('RGBA')
        
        # Processa apenas a página especificada
        page = pdf_document[page_number]
        
        for pos in positions:
            x, y = pos['x'], pos['y']
            size = pos.get('size', 50)
            
            # Redimensiona o QR
            qr_resized = qr_image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Converte para bytes
            qr_bytes = io.BytesIO()
            qr_resized.save(qr_bytes, format='PNG')
            qr_bytes = qr_bytes.getvalue()
            
            # Insere o QR na página
            rect = fitz.Rect(x, y, x + size, y + size)
            page.insert_image(rect, stream=qr_bytes)
        
        # Salva em memória
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
    """Salva todas as páginas do PDF com QR Codes inseridos"""
    try:
        pdf_file = request.files.get('pdf')
        qr_file = request.files.get('qr')
        all_positions_str = request.form.get('allPositions', '{}')
        
        if not pdf_file or not qr_file:
            return jsonify({'error': 'PDF e QR Code são obrigatórios'}), 400
        
        all_positions = eval(all_positions_str) if all_positions_str else {}
        
        # Abre o PDF
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        
        # Carrega a imagem do QR
        qr_image = Image.open(qr_file).convert('RGBA')
        
        # Processa todas as páginas com QRs
        for page_num, positions in all_positions.items():
            if not positions:  # Pula páginas sem QRs
                continue
                
            page_index = int(page_num)
            if page_index >= len(pdf_document):
                continue
                
            page = pdf_document[page_index]
            
            for pos in positions:
                x, y = pos['x'], pos['y']
                size = pos.get('size', 50)
                
                # Redimensiona o QR
                qr_resized = qr_image.resize((size, size), Image.Resampling.LANCZOS)
                
                # Converte para bytes
                qr_bytes = io.BytesIO()
                qr_resized.save(qr_bytes, format='PNG')
                qr_bytes = qr_bytes.getvalue()
                
                # Insere o QR na página
                rect = fitz.Rect(x, y, x + size, y + size)
                page.insert_image(rect, stream=qr_bytes)
        
        # Salva em memória
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
