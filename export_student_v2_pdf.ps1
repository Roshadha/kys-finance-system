$ErrorActionPreference = 'Stop'
$docx = 'C:\Users\user\Desktop\New folder (11)\output\Grade_10_Chinese_Complete_Workbook_Translation_and_Essay_Edition.docx'
$pdf = 'C:\Users\user\Desktop\New folder (11)\output\Grade_10_Chinese_Complete_Workbook_Translation_and_Essay_Edition.pdf'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $document = $word.Documents.Open($docx, $false, $true)
    $document.ExportAsFixedFormat($pdf, 17)
    $pages = $document.ComputeStatistics(2)
    Write-Output "Exported $pages pages to $pdf"
    $document.Close($false)
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
}
