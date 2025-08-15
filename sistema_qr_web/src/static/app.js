// Estado global da aplicação
let appState = {
    currentPdf: null,
    currentPage: 0,
    totalPages: 0,
    pages: [],
    qrImage: null,
    qrPositions: [],
    batchPdfs: [],
    batchQrs: [],
    extractedQrs: []
};

// Configuração da API
const API_BASE = '/api';

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    log('Sistema iniciado. Carregue um PDF e QR Code para começar.');
});

function setupEventListeners() {
    // Slider de tamanho do QR
    const qrSizeSlider = document.getElementById('qrSizeSlider');
    qrSizeSlider.addEventListener('input', function() {
        document.getElementById('qrSizeLabel').textContent = this.value + '%';
    });

    // Drag and drop para PDFs
    const pdfCanvas = document.getElementById('pdfCanvas');
    pdfCanvas.addEventListener('dragover', handleDragOver);
    pdfCanvas.addEventListener('drop', handleDrop);
    pdfCanvas.addEventListener('click', handleCanvasClick);
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    const pdfFiles = files.filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length > 0) {
        loadPdfs(pdfFiles);
    }
}

function handleCanvasClick(e) {
    if (!appState.qrImage || !appState.currentPdf) {
        if (!appState.qrImage) {
            alert('Carregue um QR Code primeiro!');
        } else {
            alert('Carregue um PDF primeiro!');
        }
        return;
    }

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    const qrSize = parseInt(document.getElementById('qrSizeSlider').value);
    const canvasWidth = rect.width;
    const canvasHeight = rect.height;
    const minSide = Math.min(canvasWidth, canvasHeight);
    const qrPixelSize = (qrSize / 100) * minSide;
    
        // Ajusta para garantir que o QR fique dentro da área do diploma (imagem renderizada)
        // Supondo que a imagem é centralizada e tem margens laterais
        const diplomaMarginX = canvasWidth * 0.07; // 7% de margem lateral
        const diplomaMarginY = canvasHeight * 0.07; // 7% de margem vertical
        const diplomaWidth = canvasWidth - 2 * diplomaMarginX;
        const diplomaHeight = canvasHeight - 2 * diplomaMarginY;

        // Limites válidos para o centro do QR
        const minX = diplomaMarginX + qrPixelSize / 2;
        const maxX = diplomaMarginX + diplomaWidth - qrPixelSize / 2;
        const minY = diplomaMarginY + qrPixelSize / 2;
        const maxY = diplomaMarginY + diplomaHeight - qrPixelSize / 2;

        // Ajusta a posição para ficar dentro do diploma
        const qrCenterX = Math.max(minX, Math.min(x, maxX));
        const qrCenterY = Math.max(minY, Math.min(y, maxY));
        const qrX = qrCenterX - qrPixelSize / 2;
        const qrY = qrCenterY - qrPixelSize / 2;
    
    // Remove QR anterior desta página
    if (!appState.qrPositions[appState.currentPage]) {
        appState.qrPositions[appState.currentPage] = [];
    }
    appState.qrPositions[appState.currentPage] = [];
    
    // Adiciona novo QR
    appState.qrPositions[appState.currentPage].push({
        x: qrX,
        y: qrY,
        size: qrPixelSize,
        percent: qrSize,
        canvas_width: canvasWidth,
        canvas_height: canvasHeight
    });
    
    drawQrOverlays();
    updateSaveButtons();
    log(`QR Code posicionado na página ${appState.currentPage + 1} em (${Math.round(qrX)}, ${Math.round(qrY)})`);
}

async function loadPdfs(files) {
    if (!files || files.length === 0) return;
    
    showLoading('Carregando PDFs...');
    
    try {
        appState.batchPdfs = Array.from(files);
        updateFilesList();
        log(`Carregados ${files.length} PDFs em lote`);
        
        // Carrega o primeiro PDF para preview
        if (files.length > 0) {
            await loadSinglePdf(files[0]);
        }
        
        updateStatus();
    } catch (error) {
        log(`Erro ao carregar PDFs: ${error.message}`);
        alert('Erro ao carregar PDFs: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function loadSinglePdf(file) {
    const formData = new FormData();
    formData.append('pdf', file);
    
    const response = await fetch(`${API_BASE}/upload-pdf`, {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    
    if (result.success) {
        appState.currentPdf = file;
        appState.pages = result.pages;
        appState.totalPages = result.total_pages;
        appState.currentPage = 0;
        appState.qrPositions = new Array(appState.totalPages).fill(null).map(() => []);
        
        renderCurrentPage();
        updateNavigation();
        updateSaveButtons();
        
        log(`PDF carregado: ${file.name} (${appState.totalPages} páginas)`);
    } else {
        throw new Error(result.error);
    }
}

async function loadQrs(files) {
    if (!files || files.length === 0) return;
    
    appState.batchQrs = Array.from(files);
    updateFilesList();
    log(`Carregados ${files.length} QR Codes em lote`);
    
    // Carrega o primeiro QR para preview
    if (files.length > 0) {
        const file = files[0];
        const reader = new FileReader();
        reader.onload = function(e) {
            appState.qrImage = e.target.result;
            updateQrPreview();
            updateStatus();
            updateSaveButtons();
            log(`QR Code carregado: ${file.name}`);
        };
        reader.readAsDataURL(file);
    }
}

function updateQrPreview() {
    const qrPreview = document.getElementById('qrPreview');
    const qrPreviewImage = document.getElementById('qrPreviewImage');
    
    if (appState.qrImage) {
        qrPreviewImage.style.backgroundImage = `url(${appState.qrImage})`;
        qrPreview.style.display = 'block';
    } else {
        qrPreview.style.display = 'none';
    }
}

function removeAllQrsFromPage() {
    if (appState.qrPositions[appState.currentPage]) {
        appState.qrPositions[appState.currentPage] = [];
        drawQrOverlays();
        updateSaveButtons();
        log(`Todos os QR Codes removidos da página ${appState.currentPage + 1}`);
    }
}

async function extractQrs(files) {
    if (!files || files.length === 0) return;
    
    showLoading('Extraindo QR Codes...');
    
    try {
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('pdfs', file);
        });
        
        const response = await fetch(`${API_BASE}/extract-qr`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            appState.extractedQrs = result.extracted_qrs;
            
            // Converte QRs extraídos para formato de arquivo
            appState.batchQrs = result.extracted_qrs.map(qr => ({
                name: qr.filename,
                dataUrl: qr.image
            }));
            
            // Carrega o primeiro QR extraído
            if (result.extracted_qrs.length > 0) {
                appState.qrImage = result.extracted_qrs[0].image;
            }
            
            updateFilesList();
            updateStatus();
            updateSaveButtons();
            
            log(`${result.total_extracted} QR Codes extraídos com sucesso!`);
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        log(`Erro ao extrair QR Codes: ${error.message}`);
        alert('Erro ao extrair QR Codes: ' + error.message);
    } finally {
        hideLoading();
    }
}

function renderCurrentPage() {
    if (!appState.pages || appState.pages.length === 0) return;
    
    const pdfCanvas = document.getElementById('pdfCanvas');
    const page = appState.pages[appState.currentPage];
    
    pdfCanvas.innerHTML = `
        <img src="${page.image}" 
             class="pdf-image" 
             alt="Página ${appState.currentPage + 1}"
             style="position: relative;">
    `;
    
    pdfCanvas.classList.add('has-pdf');
    
    // Aguarda a imagem carregar para desenhar overlays
    const img = pdfCanvas.querySelector('.pdf-image');
    img.onload = () => {
        drawQrOverlays();
    };
}

function drawQrOverlays() {
    // Remove overlays existentes
    document.querySelectorAll('.qr-overlay').forEach(el => el.remove());
    
    if (!appState.qrPositions[appState.currentPage] || !appState.qrImage) return;
    
    const pdfCanvas = document.getElementById('pdfCanvas');
    const pageQrs = appState.qrPositions[appState.currentPage];
    
    pageQrs.forEach((qr, index) => {
        const overlay = document.createElement('div');
        overlay.className = 'qr-overlay';
        overlay.style.left = Math.max(0, qr.x) + 'px';
        overlay.style.top = Math.max(0, qr.y) + 'px';
        overlay.style.width = qr.size + 'px';
        overlay.style.height = qr.size + 'px';
        overlay.style.backgroundImage = `url(${appState.qrImage})`;
        overlay.style.backgroundSize = 'contain';
        overlay.style.backgroundRepeat = 'no-repeat';
        overlay.style.backgroundPosition = 'center';
        overlay.style.border = '2px solid #ff4757';
        overlay.style.cursor = 'pointer';
        overlay.title = 'Clique para remover o QR Code';
        
        // Adiciona evento de clique para remover
        overlay.addEventListener('click', function(e) {
            e.stopPropagation();
            removeQrFromPage(appState.currentPage, index);
        });
        
        pdfCanvas.appendChild(overlay);
    });
}

function removeQrFromPage(pageIndex, qrIndex) {
    if (appState.qrPositions[pageIndex]) {
        appState.qrPositions[pageIndex].splice(qrIndex, 1);
        drawQrOverlays();
        updateSaveButtons();
        log(`QR Code removido da página ${pageIndex + 1}`);
    }
}

function previousPage() {
    if (appState.currentPage > 0) {
        appState.currentPage--;
        renderCurrentPage();
        updateNavigation();
    }
}

function nextPage() {
    if (appState.currentPage < appState.totalPages - 1) {
        appState.currentPage++;
        renderCurrentPage();
        updateNavigation();
    }
}

function updateNavigation() {
    const navigation = document.getElementById('navigation');
    const pageInfo = document.getElementById('pageInfo');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    
    if (appState.totalPages > 0) {
        navigation.classList.remove('hidden');
        pageInfo.textContent = `Página ${appState.currentPage + 1} de ${appState.totalPages}`;
        prevBtn.disabled = appState.currentPage === 0;
        nextBtn.disabled = appState.currentPage === appState.totalPages - 1;
    } else {
        navigation.classList.add('hidden');
    }
}

function updateFilesList() {
    const fileList = document.getElementById('fileList');
    let html = '';
    
    if (appState.batchPdfs.length > 0) {
        html += '<div style="font-weight: bold; color: #667eea;">📄 PDFs</div>';
        appState.batchPdfs.forEach(file => {
            html += `<div class="file-item">📄 ${file.name}</div>`;
        });
    }
    
    if (appState.batchQrs.length > 0) {
        html += '<div style="font-weight: bold; color: #667eea; margin-top: 10px;">🖼 QR Codes</div>';
        appState.batchQrs.forEach(qr => {
            const name = qr.name || qr.filename || 'QR Code';
            html += `<div class="file-item">🖼 ${name}</div>`;
        });
    }
    
    if (html === '') {
        html = '<div class="file-item">Nenhum arquivo carregado</div>';
    }
    
    fileList.innerHTML = html;
}

function updateStatus() {
    const pdfStatus = document.getElementById('pdfStatus');
    const qrStatus = document.getElementById('qrStatus');
    
    if (appState.batchPdfs.length > 0) {
        pdfStatus.textContent = `${appState.batchPdfs.length} PDF(s) carregado(s)`;
    } else {
        pdfStatus.textContent = 'Nenhum PDF carregado';
    }
    
    if (appState.batchQrs.length > 0 || appState.qrImage) {
        qrStatus.textContent = `${appState.batchQrs.length || 1} QR Code(s) carregado(s)`;
    } else {
        qrStatus.textContent = 'Nenhum QR Code carregado';
    }
}

function updateSaveButtons() {
    const savePdfBtn = document.getElementById('savePdfBtn');
    const saveBatchBtn = document.getElementById('saveBatchBtn');
    const saveCurrentPageBtn = document.getElementById('saveCurrentPage');
    const saveAllPagesBtn = document.getElementById('saveAllPages');
    const processInBatchBtn = document.getElementById('processInBatch');
    
    const hasQrPositioned = appState.qrPositions.some(positions => positions.length > 0);
    const canSave = appState.currentPdf && appState.qrImage && hasQrPositioned;
    const canSaveBatch = appState.batchPdfs.length > 0 && appState.batchQrs.length > 0;
    const hasCurrentPageQr = appState.qrPositions[appState.currentPage] && appState.qrPositions[appState.currentPage].length > 0;
    const canProcessBatch = appState.currentPdf && appState.batchQrs && appState.batchQrs.length > 0;
    
    if (savePdfBtn) savePdfBtn.disabled = !canSave;
    if (saveBatchBtn) saveBatchBtn.disabled = !canSaveBatch;
    if (saveCurrentPageBtn) saveCurrentPageBtn.disabled = !hasCurrentPageQr;
    if (saveAllPagesBtn) saveAllPagesBtn.disabled = !canSave;
    if (processInBatchBtn) processInBatchBtn.disabled = !canProcessBatch;
}

function removeQrFromPage() {
    if (appState.qrPositions[appState.currentPage]) {
        appState.qrPositions[appState.currentPage] = [];
        drawQrOverlays();
        updateSaveButtons();
        log(`QR Code removido da página ${appState.currentPage + 1}`);
    }
}

async function savePdf() {
    if (!appState.currentPdf || !appState.qrImage) {
        alert('Carregue um PDF e QR Code primeiro!');
        return;
    }
    
    showLoading('Salvando PDF...');
    
    try {
        // Converte PDF para base64
        const pdfBase64 = await fileToBase64(appState.currentPdf);
        
        // Prepara posições dos QRs
        const qrPositions = [];
        appState.qrPositions.forEach((positions, pageIndex) => {
            positions.forEach(pos => {
                qrPositions.push({
                    page: pageIndex,
                    x: pos.x,
                    y: pos.y,
                    size: pos.size,
                    canvas_width: pos.canvas_width,
                    canvas_height: pos.canvas_height
                });
            });
        });
        
        const response = await fetch(`${API_BASE}/insert-qr`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pdf_base64: pdfBase64,
                qr_base64: appState.qrImage,
                qr_positions: qrPositions
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            downloadBase64File(result.pdf_base64, 'pdf_com_qr.pdf');
            log('PDF salvo com sucesso!');
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        log(`Erro ao salvar PDF: ${error.message}`);
        alert('Erro ao salvar PDF: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function saveBatchZip() {
    if (appState.batchPdfs.length === 0 || appState.batchQrs.length === 0) {
        alert('Carregue PDFs e QR Codes em lote primeiro!');
        return;
    }
    
    showLoading('Processando lote...');
    
    try {
        const formData = new FormData();
        
        appState.batchPdfs.forEach(file => {
            formData.append('pdfs', file);
        });
        
        // Se temos QRs extraídos, usa eles; senão usa os arquivos carregados
        if (appState.extractedQrs.length > 0) {
            // Para QRs extraídos, precisamos converter de base64 para File
            for (const qr of appState.extractedQrs) {
                const blob = await base64ToBlob(qr.image);
                const file = new File([blob], qr.filename, { type: 'image/png' });
                formData.append('qrs', file);
            }
        } else {
            appState.batchQrs.forEach(file => {
                formData.append('qrs', file);
            });
        }
        
        const response = await fetch(`${API_BASE}/batch-process`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Cria ZIP com os PDFs processados
            const zip = new JSZip();
            
            result.processed_pdfs.forEach(pdf => {
                const base64Data = pdf.pdf_base64.split(',')[1];
                zip.file(pdf.filename, base64Data, { base64: true });
            });
            
            const zipBlob = await zip.generateAsync({ type: 'blob' });
            downloadBlob(zipBlob, 'pdfs_processados.zip');
            
            log(`${result.total_processed} PDFs processados e salvos em ZIP!`);
        } else {
            throw new Error(result.error);
        }
    } catch (error) {
        log(`Erro no processamento em lote: ${error.message}`);
        alert('Erro no processamento em lote: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function saveCurrentPage() {
    if (!appState.currentPdf || !appState.qrImage) {
        alert('Carregue um PDF e QR Code primeiro.');
        return;
    }
    
    const pageQrs = appState.qrPositions[appState.currentPage] || [];
    if (pageQrs.length === 0) {
        alert('Adicione pelo menos um QR Code à página atual.');
        return;
    }
    
    try {
        log(`Salvando página ${appState.currentPage + 1} com ${pageQrs.length} QR Code(s)...`);
        
        const formData = new FormData();
        formData.append('pdf', appState.currentPdf);
        formData.append('qr', await fetch(appState.qrImage).then(r => r.blob()));
        formData.append('pageNumber', appState.currentPage.toString());
        formData.append('positions', JSON.stringify(pageQrs));
        
        const response = await fetch('/api/save-page', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const blob = await response.blob();
            downloadBlob(blob, `diploma_pagina_${appState.currentPage + 1}.pdf`);
            log(`Página ${appState.currentPage + 1} salva com sucesso!`);
        } else {
            const error = await response.text();
            log(`Erro ao salvar página: ${error}`, 'error');
        }
    } catch (error) {
        log(`Erro durante o salvamento: ${error.message}`, 'error');
    }
}

async function saveAllPages() {
    if (!appState.currentPdf || !appState.qrImage) {
        alert('Carregue um PDF e QR Code primeiro.');
        return;
    }
    
    const totalQrs = Object.values(appState.qrPositions).reduce((sum, page) => sum + page.length, 0);
    if (totalQrs === 0) {
        alert('Adicione pelo menos um QR Code antes de salvar.');
        return;
    }
    
    try {
        log(`Salvando todas as páginas com ${totalQrs} QR Code(s)...`);
        
        const formData = new FormData();
        formData.append('pdf', appState.currentPdf);
        formData.append('qr', await fetch(appState.qrImage).then(r => r.blob()));
        formData.append('allPositions', JSON.stringify(appState.qrPositions));
        
        const response = await fetch('/api/save-all-pages', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const blob = await response.blob();
            downloadBlob(blob, 'diploma_completo_com_qrs.pdf');
            log('Todas as páginas salvas com sucesso!');
        } else {
            const error = await response.text();
            log(`Erro ao salvar todas as páginas: ${error}`, 'error');
        }
    } catch (error) {
        log(`Erro durante o salvamento: ${error.message}`, 'error');
    }
}

function resetSystem() {
    appState = {
        currentPdf: null,
        currentPage: 0,
        totalPages: 0,
        pages: [],
        qrImage: null,
        qrPositions: [],
        batchPdfs: [],
        batchQrs: [],
        extractedQrs: []
    };
    
    // Reset UI
    document.getElementById('pdfCanvas').innerHTML = `
        <div class="upload-area" onclick="document.getElementById('pdfInput').click()">
            <h3>📄 Carregue um PDF para começar</h3>
            <p>Clique aqui ou arraste arquivos PDF</p>
        </div>
    `;
    document.getElementById('pdfCanvas').classList.remove('has-pdf');
    document.getElementById('navigation').classList.add('hidden');
    document.getElementById('qrSizeSlider').value = 20;
    document.getElementById('qrSizeLabel').textContent = '20%';
    
    // Reset inputs
    document.getElementById('pdfInput').value = '';
    document.getElementById('qrInput').value = '';
    document.getElementById('extractPdfInput').value = '';
    
    updateFilesList();
    updateStatus();
    updateSaveButtons();
    
    log('Sistema reiniciado. Carregue um PDF e QR Code para começar.');
}

// Funções utilitárias
function log(message) {
    const logArea = document.getElementById('logArea');
    const timestamp = new Date().toLocaleTimeString();
    logArea.innerHTML += `<div>[${timestamp}] ${message}</div>`;
    logArea.scrollTop = logArea.scrollHeight;
}

function showLoading(text = 'Processando...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingModal').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loadingModal').style.display = 'none';
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

function base64ToBlob(base64) {
    return new Promise((resolve) => {
        const base64Data = base64.split(',')[1];
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: 'image/png' });
        resolve(blob);
    });
}

function downloadBase64File(base64Data, filename) {
    const link = document.createElement('a');
    link.href = base64Data;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Adiciona JSZip para criação de arquivos ZIP
const script = document.createElement('script');
script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
document.head.appendChild(script);

// Funções adicionais
async function processInBatch() {
    if (!appState.pdfUrl || !appState.batchQrs || appState.batchQrs.length === 0) {
        alert('Carregue um PDF e QR Codes antes de processar em lote.');
        return;
    }

    const progress = document.getElementById('batchProgress');
    if (progress) {
        const progressBar = progress.querySelector('.progress');
        progress.style.display = 'block';
    }

    try {
        log('Iniciando processamento em lote...');
        
        const formData = new FormData();
        formData.append('pdf', await fetch(appState.pdfUrl).then(r => r.blob()));
        
        for (let i = 0; i < appState.batchQrs.length; i++) {
            formData.append('qrs', appState.batchQrs[i]);
        }

        const response = await fetch('/api/batch-process', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            downloadBlob(blob, 'diploma_com_qrs_lote.pdf');
            log('Processamento em lote concluído com sucesso!');
        } else {
            const error = await response.text();
            log(`Erro no processamento em lote: ${error}`, 'error');
        }
    } catch (error) {
        log(`Erro durante o processamento em lote: ${error.message}`, 'error');
    } finally {
        if (progress) {
            progress.style.display = 'none';
        }
    }
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function updateQrPreview() {
    const qrPreview = document.getElementById('qrPreview');
    const qrPreviewImage = document.getElementById('qrPreviewImage');
    
    if (appState.qrImage && qrPreview && qrPreviewImage) {
        qrPreviewImage.style.backgroundImage = `url(${appState.qrImage})`;
        qrPreview.style.display = 'block';
    } else if (qrPreview) {
        qrPreview.style.display = 'none';
    }
}

function removeAllQrsFromPage() {
    if (appState.qrPositions[appState.currentPage]) {
        appState.qrPositions[appState.currentPage] = [];
        drawQrOverlays();
        updateSaveButtons();
        log(`Todos os QR Codes removidos da página ${appState.currentPage + 1}`);
    }
}

