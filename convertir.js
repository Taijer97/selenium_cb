const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

async function convertirHTMLaPDF(archivoHTML = 'arch.html', archivoPDF = null) {
    let browser;
    
    try {
        // Si no se especifica PDF, usar el mismo nombre que HTML
        if (!archivoPDF) {
            const nombreBase = path.parse(archivoHTML).name;
            archivoPDF = `${nombreBase}.pdf`;
        }
        
        // Verificar que el archivo HTML existe
        if (!fs.existsSync(archivoHTML)) {
            throw new Error(`No se encontró el archivo: ${archivoHTML}`);
        }
        
        console.log('Iniciando Puppeteer...');
        browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const page = await browser.newPage();
        
        // Cargar el archivo HTML
        const rutaCompleta = path.resolve(archivoHTML);
        const urlArchivo = `file://${rutaCompleta}`;
        
        console.log(`Cargando: ${urlArchivo}`);
        await page.goto(urlArchivo, { 
            waitUntil: 'networkidle0',
            timeout: 30000 
        });
        
        // Configuración del PDF
        const opcionesPDF = {
            path: archivoPDF,
            format: 'A4',
            printBackground: true,
            margin: {
                top: '20px',
                right: '20px',
                bottom: '20px',
                left: '20px'
            }
        };
        
        console.log('Generando PDF...');
        await page.pdf(opcionesPDF);
        
        console.log(`PDF creado exitosamente: ${archivoPDF}`);
        return true;
        
    } catch (error) {
        console.error('Error al convertir:', error.message);
        return false;
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

// Si se ejecuta directamente
if (require.main === module) {
    const archivoHTML = process.argv[2] || 'arch.html';
    const archivoPDF = process.argv[3] || null;
    
    convertirHTMLaPDF(archivoHTML, archivoPDF)
        .then(exito => {
            process.exit(exito ? 0 : 1);
        });
}

module.exports = { convertirHTMLaPDF };