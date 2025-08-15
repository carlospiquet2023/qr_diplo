// Funções para manipulação de arquivos e downloads
function saveZip(files, fileName) {
    const zip = new JSZip();
    files.forEach(file => {
        const base64Data = file.pdf_base64.split(',')[1];
        zip.file(file.filename, base64Data, { base64: true });
    });
    zip.generateAsync({ type: 'blob' }).then(blob => {
        downloadBlob(blob, fileName);
    });
}
