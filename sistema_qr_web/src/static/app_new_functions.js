// Funções para manipulação de arquivos e downloads
async function saveZip(files, fileName) {
    log('Criando arquivo ZIP...');
    const zip = new JSZip();
    files.forEach(file => {
        const base64Data = file.pdf_base64.split(',')[1];
        zip.file(file.filename, base64Data, { base64: true });
    });
    const blob = await zip.generateAsync({ type: 'blob' });
    downloadBlob(blob, fileName);
    log('Arquivo ZIP pronto para download.');
}
