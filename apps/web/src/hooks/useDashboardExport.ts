function hideExportButtons(root: HTMLElement, hide: boolean) {
    root.querySelectorAll('[data-export-hide]').forEach((el) => {
        (el as HTMLElement).style.visibility = hide ? 'hidden' : ''
    })
}

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
}

export async function exportPng(element: HTMLElement, filename: string) {
    const html2canvas = (await import('html2canvas')).default
    hideExportButtons(element, true)
    try {
        const canvas = await html2canvas(element, { scale: 2, useCORS: true, backgroundColor: '#ffffff' })
        const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'))
        if (blob) downloadBlob(blob, filename)
    } finally {
        hideExportButtons(element, false)
    }
}

export async function exportPdf(element: HTMLElement, filename: string) {
    const html2canvas = (await import('html2canvas')).default
    const { jsPDF } = await import('jspdf')
    hideExportButtons(element, true)
    try {
        const canvas = await html2canvas(element, { scale: 2, useCORS: true, backgroundColor: '#ffffff' })
        const imgData = canvas.toDataURL('image/png')
        const pdf = new jsPDF('p', 'mm', 'a4')
        const pageWidth = pdf.internal.pageSize.getWidth()
        const pageHeight = pdf.internal.pageSize.getHeight()
        const imgWidth = pageWidth
        const imgHeight = (canvas.height * imgWidth) / canvas.width
        let heightLeft = imgHeight
        let position = 0

        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
        heightLeft -= pageHeight

        while (heightLeft > 0) {
            position = heightLeft - imgHeight
            pdf.addPage()
            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
            heightLeft -= pageHeight
        }

        pdf.save(filename)
    } finally {
        hideExportButtons(element, false)
    }
}
