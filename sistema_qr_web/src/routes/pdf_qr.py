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
    """Remove acentos e caracteres especiais do nome do arquivo"""
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(char for char in nome if unicodedata.category(char) != 'Mn')
    nome = re.sub(r'[^\w\s-]', '', nome)
    nome = re.sub(r'[-\s]+', '_', nome)
    return nome.strip('_')

def extrair_nome_do_pdf(pdf_bytes):
    """Extrai o nome do aluno do PDF"""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        text = page.get_text()
        doc.close()
        
        # Primeiro tenta o padrão "Nome do aluno:"
        match = re.search(r'Nome do aluno:\s*(.+)', text, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            nome = limpar_nome_arquivo(nome)
            if nome.lower().endswith('.pdf'):
                nome = nome[:-4]
            return nome
        
        # Para diplomas, procura por padrões de nomes próprios
        # Busca por sequências de 2+ palavras que começam com maiúscula
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Ignora linhas muito curtas ou muito longas
            if len(line) < 5 or len(line) > 50:
                continue
            
            # Procura por padrão de nome (palavras com primeira letra maiúscula)
            words = line.split()
            if len(words) >= 2:
                # Verifica se todas as palavras começam com maiúscula (exceto conectores)
                conectores = ['de', 'da', 'do', 'dos', 'das', 'e']
                nome_valido = True
                for word in words:
                    if word.lower() not in conectores and not word[0].isupper():
                        nome_valido = False
                        break
                
                if nome_valido:
                    # Verifica se não contém números ou símbolos estranhos
                    if not re.search(r'[0-9@#$%^&*()_+={}|\\:";\'<>?,.\/]', line):
                        # Verifica se não é uma palavra comum de diploma
                        palavras_ignorar = ['diploma', 'certificado', 'curso', 'universidade', 
                                          'faculdade', 'instituto', 'graduação', 'bacharelado',
                                          'licenciatura', 'tecnólogo', 'especialização', 'mestrado',
                                          'doutorado', 'pós-graduação', 'conclusão', 'formatura']
                        
                        if not any(palavra in line.lower() for palavra in palavras_ignorar):
                            nome = limpar_nome_arquivo(line)
                            if nome.lower().endswith('.pdf'):
                                nome = nome[:-4]
                            print(f"Nome extraído do diploma: {nome}")
                            return nome
        
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
            
            pages.append({
                'page_num': page_num,
                'image': f"data:image/png;base64,{img_base64}",
                'width': pix.width,
                'height': pix.height
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
                
                # Converte coordenadas da tela para coordenadas do PDF
                page_rect = page.rect
                scale_x = page_rect.width / position['canvas_width']
                scale_y = page_rect.height / position['canvas_height']
                
                pdf_x = x * scale_x
                pdf_y = y * scale_y
                pdf_size = size * min(scale_x, scale_y)
                
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
    """Endpoint para processamento em lote"""
    try:
        if 'pdfs' not in request.files or 'qrs' not in request.files:
            return jsonify({'error': 'Arquivos PDF e QR são necessários'}), 400
        
        pdf_files = request.files.getlist('pdfs')
        qr_files = request.files.getlist('qrs')
        
        processing_log = []
        print("Iniciando processamento em lote...")
        processing_log.append("Iniciando processamento em lote...")
        
        # Cria um dicionário de QRs por nome (com normalização)
        qr_dict = {}
        for qr_file in qr_files:
            if qr_file.filename:
                qr_name = os.path.splitext(qr_file.filename)[0]
                qr_name_normalizado = limpar_nome_arquivo(qr_name)
                qr_dict[qr_name_normalizado] = Image.open(qr_file.stream)
                qr_dict[qr_name] = qr_dict[qr_name_normalizado]  # Mantém também o original
                print(f"QR carregado: {qr_name} -> {qr_name_normalizado}")
                processing_log.append(f"QR carregado: {qr_name}")
        
        print(f"Total de QRs carregados: {len(set(qr_dict.keys()))}")
        processing_log.append(f"Total de QRs únicos: {len(set(qr_dict.keys()))}")
        
        processed_pdfs = []
        
        for pdf_file in pdf_files:
            if pdf_file.filename == '':
                continue
            
            print(f"Processando PDF: {pdf_file.filename}")
            processing_log.append(f"Processando PDF: {pdf_file.filename}")
            
            pdf_bytes = pdf_file.read()
            nome_aluno = extrair_nome_do_pdf(pdf_bytes)
            
            if not nome_aluno:
                msg = f"Nome não encontrado em {pdf_file.filename}"
                print(msg)
                processing_log.append(msg)
                continue
            
            print(f"Nome extraído: {nome_aluno}")
            processing_log.append(f"Nome extraído: {nome_aluno}")
            
            # Tenta encontrar QR correspondente (várias estratégias)
            qr_image = None
            qr_match_key = None
            
            # 1. Tentativa exata
            if nome_aluno in qr_dict:
                qr_image = qr_dict[nome_aluno]
                qr_match_key = nome_aluno
                print(f"Match exato encontrado: {nome_aluno}")
            
            # 2. Tentativa com normalização
            elif nome_aluno.lower() in [k.lower() for k in qr_dict.keys()]:
                for k in qr_dict.keys():
                    if k.lower() == nome_aluno.lower():
                        qr_image = qr_dict[k]
                        qr_match_key = k
                        print(f"Match por normalização: {nome_aluno} -> {k}")
                        break
            
            # 3. Tentativa parcial (nome contém ou é contido)
            else:
                for qr_name in qr_dict.keys():
                    if (nome_aluno.lower() in qr_name.lower() or 
                        qr_name.lower() in nome_aluno.lower()):
                        qr_image = qr_dict[qr_name]
                        qr_match_key = qr_name
                        print(f"Match parcial: {nome_aluno} -> {qr_name}")
                        break
            
            if not qr_image:
                msg = f"QR não encontrado para {nome_aluno}"
                print(msg)
                processing_log.append(msg)
                continue
            
            processing_log.append(f"QR encontrado: {qr_match_key}")
            
            # Processa o PDF
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Insere QR na primeira página (canto inferior direito)
            if len(doc) > 0:
                page = doc[0]
                page_rect = page.rect
                qr_size = min(page_rect.width, page_rect.height) * 0.15  # 15% do menor lado
                
                x = page_rect.width - qr_size - 20
                y = page_rect.height - qr_size - 20
                
                qr_resized = qr_image.resize((int(qr_size), int(qr_size)), Image.Resampling.LANCZOS)
                qr_bytes = io.BytesIO()
                qr_resized.save(qr_bytes, format='PNG')
                qr_bytes.seek(0)
                
                rect = fitz.Rect(x, y, x + qr_size, y + qr_size)
                page.insert_image(rect, stream=qr_bytes.getvalue())
                
                print(f"QR inserido em {nome_aluno}")
                processing_log.append(f"QR inserido com sucesso")
            
            # Salva PDF processado
            output_buffer = io.BytesIO()
            doc.save(output_buffer)
            doc.close()
            
            output_buffer.seek(0)
            pdf_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            
            processed_pdfs.append({
                'filename': f"{nome_aluno}_com_qr.pdf",
                'pdf_base64': f"data:application/pdf;base64,{pdf_base64}",
                'original_name': nome_aluno,
                'qr_matched': qr_match_key
            })
        
        result_msg = f"Processamento concluído: {len(processed_pdfs)} PDFs processados"
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
        return jsonify({'error': f'Erro no processamento em lote: {str(e)}'}), 500

