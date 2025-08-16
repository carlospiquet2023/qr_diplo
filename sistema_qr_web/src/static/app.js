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
    extractedQrs: [],
    viewMode: 'fit' // 'fit' ou 'real'
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
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    const pdfImage = e.currentTarget.querySelector('.pdf-image');
    if (!pdfImage) return;
    
    const imageRect = pdfImage.getBoundingClientRect();
    const canvasRect = rect;
    
    // Coordenadas relativas à imagem
    const relativeX = clickX - (imageRect.left - canvasRect.left);
    const relativeY = clickY - (imageRect.top - canvasRect.top);
    
    // Verifica se o clique foi dentro da imagem
    if (relativeX < 0 || relativeY < 0 || relativeX > imageRect.width || relativeY > imageRect.height) {
        return; // Clique fora da imagem
    }
    
    // Obtém as dimensões reais do PDF
    const realDimensions = getRealPdfDimensions();
    if (!realDimensions) return;
    
    // Calcula a escala da imagem exibida vs. tamanho real
    let scaleX, scaleY;
    if (appState.viewMode === 'real') {
        // No modo real, assumimos que a imagem está em 1:1
        scaleX = realDimensions.width / imageRect.width;
        scaleY = realDimensions.height / imageRect.height;
    } else {
        // No modo fit, calculamos com base no tamanho real
        scaleX = realDimensions.width / imageRect.width;
        scaleY = realDimensions.height / imageRect.height;
    }
    
    // Converte para coordenadas reais do PDF
    const realX = relativeX * scaleX;
    const realY = relativeY * scaleY;
    
    // Calcula o tamanho do QR em coordenadas reais
    const qrSizePercent = parseInt(document.getElementById('qrSizeSlider').value);
    const minSideReal = Math.min(realDimensions.width, realDimensions.height);
    const qrRealSize = (qrSizePercent / 100) * minSideReal;
    
    // Ajusta posição para centralizar o QR no clique
    const qrRealX = realX - qrRealSize / 2;
    const qrRealY = realY - qrRealSize / 2;
    
    // Garante que o QR fique dentro dos limites do PDF
    const finalX = Math.max(0, Math.min(qrRealX, realDimensions.width - qrRealSize));
    const finalY = Math.max(0, Math.min(qrRealY, realDimensions.height - qrRealSize));
    
    // Remove QR anterior desta página
    if (!appState.qrPositions[appState.currentPage]) {
        appState.qrPositions[appState.currentPage] = [];
    }
    appState.qrPositions[appState.currentPage] = [];
    
    // Adiciona novo QR com coordenadas reais
    appState.qrPositions[appState.currentPage].push({
        x: finalX,
        y: finalY,
        size: qrRealSize,
        percent: qrSizePercent,
        canvas_width: imageRect.width,
        canvas_height: imageRect.height,
        real_width: realDimensions.width,
        real_height: realDimensions.height,
        scale_x: scaleX,
        scale_y: scaleY
    });
    
    drawQrOverlays();
    updateSaveButtons();
    log(`QR Code posicionado na página ${appState.currentPage + 1} em coordenadas reais (${Math.round(finalX)}, ${Math.round(finalY)})`);
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
    
    const viewModeClass = appState.viewMode === 'real' ? 'real-size' : 'fit-screen';
    
    pdfCanvas.innerHTML = `
        <div style="position: relative; display: inline-block;">
            <img src="${page.image}" 
                 class="pdf-image ${viewModeClass}" 
                 alt="Página ${appState.currentPage + 1}">
        </div>
    `;
    
    pdfCanvas.classList.add('has-pdf');
    if (appState.viewMode === 'real') {
        pdfCanvas.classList.add('real-size');
    } else {
        pdfCanvas.classList.remove('real-size');
    }
    
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
    const pdfImage = pdfCanvas.querySelector('.pdf-image');
    const imageContainer = pdfImage ? pdfImage.parentElement : null;
    const pageQrs = appState.qrPositions[appState.currentPage];
    
    if (!pdfImage || !imageContainer) return;
    
    const imageRect = pdfImage.getBoundingClientRect();
    
    // Obtém as dimensões reais do PDF
    const realDimensions = getRealPdfDimensions();
    if (!realDimensions) return;
    
    pageQrs.forEach((qr, index) => {
        // Converte coordenadas reais para coordenadas da imagem exibida
        const scaleX = imageRect.width / realDimensions.width;
        const scaleY = imageRect.height / realDimensions.height;
        
        const displayX = qr.x * scaleX;
        const displayY = qr.y * scaleY;
        const displaySize = qr.size * Math.min(scaleX, scaleY);
        
        const overlay = document.createElement('div');
        overlay.className = 'qr-overlay';
        overlay.style.position = 'absolute';
        overlay.style.left = displayX + 'px';
        overlay.style.top = displayY + 'px';
        overlay.style.width = displaySize + 'px';
        overlay.style.height = displaySize + 'px';
        overlay.style.backgroundImage = `url(${appState.qrImage})`;
        overlay.style.backgroundSize = 'contain';
        overlay.style.backgroundRepeat = 'no-repeat';
        overlay.style.backgroundPosition = 'center';
        overlay.style.border = '2px solid #ff4757';
        overlay.style.cursor = 'pointer';
        overlay.style.zIndex = '10';
        overlay.title = 'Clique para remover o QR Code';
        
        // Adiciona evento de clique para remover
        overlay.addEventListener('click', function(e) {
            e.stopPropagation();
            removeQrFromPage(appState.currentPage, index);
        });
        
        imageContainer.appendChild(overlay);
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

async function processInBatch() {
    if (appState.batchPdfs.length === 0 || appState.batchQrs.length === 0) {
        alert('Carregue os PDFs e os QR Codes para o processamento em lote.');
        return;
    }

    const qrPosition = appState.qrPositions[appState.currentPage] && appState.qrPositions[appState.currentPage][0];
    if (!qrPosition) {
        alert('Posicione o QR Code no primeiro diploma para definir a posição para todos.');
        return;
    }

    showLoading('Processando em lote...');
    log('Iniciando processamento em lote com múltiplos QR Codes...');

    try {
        const formData = new FormData();

        // Adiciona todos os PDFs
        appState.batchPdfs.forEach(file => {
            formData.append('pdfs', file);
        });

        // Adiciona todos os QR Codes
        for (const qr of appState.batchQrs) {
            if (qr.dataUrl) {
                // QR extraído (base64)
                const blob = await base64ToBlob(qr.dataUrl);
                formData.append('qrs', blob, qr.name || 'qr.png');
            } else {
                // QR carregado (File object)
                formData.append('qrs', qr);
            }
        }

        // Adiciona a posição do QR
        formData.append('qr_position', JSON.stringify({
            x: qrPosition.x,
            y: qrPosition.y,
            size: qrPosition.size
        }));

        const response = await fetch(`${API_BASE}/batch-process`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        // Log detalhado do servidor
        if (result.processing_log) {
            result.processing_log.forEach(msg => log(msg));
        }

        if (result.success && result.processed_pdfs && result.processed_pdfs.length > 0) {
            log(`Processamento concluído. ${result.total_processed} PDFs foram processados.`);
            await saveZip(result.processed_pdfs, 'diplomas_com_qr.zip');
        } else if (result.success) {
            log('Processamento concluído, mas nenhum PDF foi retornado. Verifique os logs.');
            alert('Nenhum PDF foi processado com sucesso. Verifique a correspondência de nomes e os logs.');
        } else {
            throw new Error(result.error || 'Ocorreu um erro desconhecido no servidor.');
        }
    } catch (error) {
        log(`Erro fatal no processamento em lote: ${error.message}`);
        alert(`Erro no processamento em lote: ${error.message}`);
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


// Funções adicionais

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

// Função para alterar modo de visualização
function changeViewMode() {
    const selectedMode = document.querySelector('input[name="viewMode"]:checked').value;
    appState.viewMode = selectedMode;
    
    const pdfCanvas = document.getElementById('pdfCanvas');
    const pdfImage = pdfCanvas.querySelector('.pdf-image');
    
    if (pdfImage) {
        // Remove classes antigas
        pdfImage.classList.remove('fit-screen', 'real-size');
        pdfCanvas.classList.remove('real-size');
        
        // Aplica nova classe baseada no modo
        if (selectedMode === 'fit') {
            pdfImage.classList.add('fit-screen');
            log('Modo de visualização: Ajustar à tela');
        } else {
            pdfImage.classList.add('real-size');
            pdfCanvas.classList.add('real-size');
            log('Modo de visualização: Tamanho real (100%)');
        }
        
        // Redesenha os overlays após mudança de modo
        setTimeout(() => {
            drawQrOverlays();
        }, 100);
    }
}

// Função para obter as dimensões reais do PDF
function getRealPdfDimensions() {
    if (!appState.pages || !appState.pages[appState.currentPage]) {
        return null;
    }
    
    const page = appState.pages[appState.currentPage];
    return {
        width: page.width || 595,  // Largura padrão A4 em pontos
        height: page.height || 842 // Altura padrão A4 em pontos
    };
}
