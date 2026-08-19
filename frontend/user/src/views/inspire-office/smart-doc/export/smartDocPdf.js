import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import { downloadBlob, safeFileName } from './downloadBlob.js'
import { READING_CSS, smartDocToReadingHtml } from './smartDocReading.js'

export async function downloadSmartDocPdf(doc, { title = '未命名文档' } = {}) {
  if (!doc) throw new Error('没有可导出的文档')

  const host = document.createElement('div')
  host.setAttribute('data-sdoc-pdf-host', '')
  host.style.cssText = [
    'position:fixed',
    'left:0',
    'top:0',
    'width:794px',
    'background:#fff',
    'padding:36px 44px 48px',
    'box-sizing:border-box',
    'overflow:visible',
    'z-index:2147483000',
    'opacity:0.02',
    'pointer-events:none',
  ].join(';')
  host.innerHTML = `<style>${READING_CSS}</style>${smartDocToReadingHtml(doc, { title })}`
  document.body.appendChild(host)

  try {
    if (document.fonts?.ready) {
      try { await document.fonts.ready } catch { /* ignore */ }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 40))
    const canvas = await html2canvas(host, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      logging: false,
      windowWidth: 794,
      onclone(_clonedDoc, el) {
        el.style.opacity = '1'
      },
    })
    if (!canvas.width || !canvas.height) throw new Error('PDF 画面为空')

    const pageW = 210
    const pageH = 297
    const imgW = pageW
    const imgH = (canvas.height * pageW) / canvas.width
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' })
    const img = canvas.toDataURL('image/jpeg', 0.96)
    let offset = 0
    let first = true
    while (offset < imgH - 0.4) {
      if (!first) pdf.addPage()
      first = false
      pdf.addImage(img, 'JPEG', 0, -offset, imgW, imgH)
      offset += pageH
    }
    const blob = pdf.output('blob')
    if (!blob || blob.size < 200) throw new Error('生成的 PDF 是空文件')
    downloadBlob(safeFileName(title, 'pdf'), blob)
  } finally {
    host.remove()
  }
}
