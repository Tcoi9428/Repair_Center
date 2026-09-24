$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase

$brandOutput = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../static/branding'))
New-Item -ItemType Directory -Path $brandOutput -Force | Out-Null
$brandUtf8 = [Text.UTF8Encoding]::new($false)
$brandBlue = '#006cb5'
$brandGraphite = '#1c1e20'
$brandWhite = '#ffffff'

# Vector adaptation of the selected Module / Cyrillic РЦ concept.
# Two deliberately separated shapes keep the monogram readable in monochrome.
$brandP = 'M28 10H76C99 10 113 24 113 47V66L89 90H50V132H14V76C14 65 21 58 32 58H73C81 58 85 52 85 46C85 40 81 36 73 36H14V28C14 18 20 10 28 10Z'
$brandTs = 'M124 24Q124 14 134 14H146Q156 14 156 24V112Q164 115 164 124V140H136V132H97Q85 132 85 120V102L113 74V104H124Z'

function New-BrandMark([string]$left, [string]$right) {
    return "<path fill=`"$left`" d=`"$brandP`"/><path fill=`"$right`" d=`"$brandTs`"/>"
}

function Save-BrandSvg([string]$name, [string]$viewBox, [string]$label, [string]$content) {
    $xml = "<svg xmlns=`"http://www.w3.org/2000/svg`" viewBox=`"$viewBox`" role=`"img`" aria-label=`"$label`"><title>$label</title>$content</svg>"
    [IO.File]::WriteAllText((Join-Path $brandOutput $name), $xml, $brandUtf8)
}

$brandTypeface = [System.Windows.Media.Typeface]::new(
    [System.Windows.Media.FontFamily]::new('Segoe UI'),
    [System.Windows.FontStyles]::Normal,
    [System.Windows.FontWeights]::Bold,
    [System.Windows.FontStretches]::Normal)
$brandWord = [System.Windows.Media.FormattedText]::new(
    'Ремонтный Центр', [Globalization.CultureInfo]::GetCultureInfo('ru-RU'),
    [System.Windows.FlowDirection]::LeftToRight, $brandTypeface, 64,
    [System.Windows.Media.Brushes]::Black, 1.0)
$brandWordPath = $brandWord.BuildGeometry([System.Windows.Point]::new(0, 0)).GetOutlinedPathGeometry().ToString([Globalization.CultureInfo]::InvariantCulture)
$brandWordPath = $brandWordPath -replace '^F[01]', ''
$brandWordPath = [regex]::Replace($brandWordPath, '-?\d+\.\d+', {
    param($match)
    ([double]::Parse($match.Value, [Globalization.CultureInfo]::InvariantCulture)).ToString('0.##', [Globalization.CultureInfo]::InvariantCulture)
})
$brandLogoWidth = [int][Math]::Ceiling(146 + $brandWord.Width + 8)

$lightMark = New-BrandMark $brandBlue $brandGraphite
$darkMark = New-BrandMark $brandBlue $brandWhite
$monoMark = New-BrandMark $brandGraphite $brandGraphite
$whiteMark = New-BrandMark $brandWhite $brandWhite
$lightLogo = "<g transform=`"translate(0 4) scale(.7)`">$lightMark</g><path fill=`"$brandGraphite`" transform=`"translate(146 9)`" d=`"$brandWordPath`"/>"
$darkLogo = "<g transform=`"translate(0 4) scale(.7)`">$darkMark</g><path fill=`"$brandWhite`" transform=`"translate(146 9)`" d=`"$brandWordPath`"/>"

Save-BrandSvg 'mark-light.svg' '0 0 180 144' 'РЦ — знак для светлого фона' $lightMark
Save-BrandSvg 'mark-dark.svg' '0 0 180 144' 'РЦ — знак для графитового фона' $darkMark
Save-BrandSvg 'mark-monochrome.svg' '0 0 180 144' 'РЦ — монохромный знак' $monoMark
Save-BrandSvg 'logo-light.svg' "0 0 $brandLogoWidth 112" 'Ремонтный Центр' $lightLogo
Save-BrandSvg 'logo-dark.svg' "0 0 $brandLogoWidth 112" 'Ремонтный Центр' $darkLogo

$brandIcon = "<rect width=`"180`" height=`"180`" rx=`"36`" fill=`"$brandBlue`"/><g transform=`"translate(8 24) scale(.91)`">$whiteMark</g>"
Save-BrandSvg 'favicon.svg' '0 0 180 180' 'РЦ' $brandIcon

$brandPreviewScale = (500.0 / $brandLogoWidth).ToString('0.####', [Globalization.CultureInfo]::InvariantCulture)
$brandPreview = @"
<rect width="1120" height="660" fill="#ffffff"/>
<rect x="560" width="560" height="660" fill="#1c1e20"/>
<g font-family="Segoe UI, Arial, sans-serif" font-size="18">
<text x="34" y="44" fill="#1c1e20">РЦ / Модуль · Основная айдентика</text>
<text x="594" y="44" fill="#ffffff">Применение на графитовом фоне</text>
<g transform="translate(27 118) scale($brandPreviewScale)">$lightLogo</g>
<g transform="translate(587 118) scale($brandPreviewScale)">$darkLogo</g>
<text x="38" y="274" fill="#1c1e20">Система управления ремонтами</text>
<text x="598" y="274" fill="#ffffff">Система управления ремонтами</text>
<g transform="translate(33 326) scale(.8)">$lightMark</g>
<g transform="translate(593 326) scale(.8)">$darkMark</g>
<g transform="translate(263 316) scale(.8)">$monoMark</g>
<g transform="translate(823 316) scale(.8)">$whiteMark</g>
<text x="38" y="486" fill="#1c1e20">Иконка браузера: 16 / 24 / 32 px</text>
<text x="598" y="486" fill="#ffffff">Иконка приложения</text>
<g transform="translate(38 520) scale(.0888889)">$brandIcon</g>
<g transform="translate(96 516) scale(.1333333)">$brandIcon</g>
<g transform="translate(162 512) scale(.1777778)">$brandIcon</g>
<g transform="translate(600 510) scale(.4444444)">$brandIcon</g>
<rect x="38" y="592" width="22" height="22" rx="4" fill="#006cb5"/>
<text x="70" y="610" fill="#1c1e20">#006cb5</text>
<rect x="210" y="592" width="22" height="22" rx="4" fill="#1c1e20"/>
<text x="242" y="610" fill="#1c1e20">#1c1e20</text>
<text x="413" y="610" fill="#1c1e20">#ffffff</text>
</g>
"@
Save-BrandSvg 'brand-preview.svg' '0 0 1120 660' 'Утвержденное направление РЦ: светлое и темное применение, монохром, иконки' $brandPreview
Write-Output "Generated SVG assets: $brandOutput"
