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
        
        match = re.search(r'Nome do aluno:\s*(.+)', text, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            nome = limpar_nome_arquivo(nome)
            if nome.lower().endswith('.pdf'):
                nome = nome[:-4]
            return nome
        return None
    except Exception as e:
        print(f"Erro ao extrair nome do PDF: {e}")
        return None

def detectar_qr_code_na_imagem(img_array):
    """Detecta a posição do QR code na imagem usando OpenCV"""
    try:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
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
            return (x, y, w, h)
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
        
        for pdf_file in pdf_files:
            if pdf_file.filename == '':
                continue
                
            pdf_bytes = pdf_file.read()
            nome_aluno = extrair_nome_do_pdf(pdf_bytes)
            
            if not nome_aluno:
                continue
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            qr_found = False
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                mat = fitz.Matrix(3.0, 3.0)
                pix = page.get_pixmap(matrix=mat)
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
                        'page_num': page_num + 1
                    })
                    qr_found = True
                    break
            
            doc.close()
        
        return jsonify({
            'success': True,
            'extracted_qrs': extracted_qrs,
            'total_extracted': len(extracted_qrs)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao extrair QR codes: {str(e)}'}), 500

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
        
        # Cria um dicionário de QRs por nome
        qr_dict = {}
        for qr_file in qr_files:
            if qr_file.filename:
                qr_name = os.path.splitext(qr_file.filename)[0]
                qr_dict[qr_name] = Image.open(qr_file.stream)
        
        processed_pdfs = []
        
        for pdf_file in pdf_files:
            if pdf_file.filename == '':
                continue
            
            pdf_bytes = pdf_file.read()
            nome_aluno = extrair_nome_do_pdf(pdf_bytes)
            
            if not nome_aluno or nome_aluno not in qr_dict:
                continue
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            qr_image = qr_dict[nome_aluno]
            
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
            
            # Salva PDF processado
            output_buffer = io.BytesIO()
            doc.save(output_buffer)
            doc.close()
            
            output_buffer.seek(0)
            pdf_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            
            processed_pdfs.append({
                'filename': f"{nome_aluno}_com_qr.pdf",
                'pdf_base64': f"data:application/pdf;base64,{pdf_base64}"
            })
        
        return jsonify({
            'success': True,
            'processed_pdfs': processed_pdfs,
            'total_processed': len(processed_pdfs)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro no processamento em lote: {str(e)}'}), 500

