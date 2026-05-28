# Ícones da extensão

O arquivo `icon.svg` é a fonte. Para gerar os PNGs necessários (16x16, 48x48, 128x128) para a extensão:

## Opção 1 — Online (mais rápido)
1. Acesse https://cloudconvert.com/svg-to-png
2. Upload do `icon.svg`
3. Exporte em 3 tamanhos: 16, 48, 128
4. Salve como `icon16.png`, `icon48.png`, `icon128.png` nesta pasta

## Opção 2 — Via terminal (macOS / Linux com librsvg)
```bash
brew install librsvg  # se não tiver
cd chrome-extension/icons
rsvg-convert -w 16 -h 16 icon.svg -o icon16.png
rsvg-convert -w 48 -h 48 icon.svg -o icon48.png
rsvg-convert -w 128 -h 128 icon.svg -o icon128.png
```

## Opção 3 — Inkscape
```bash
inkscape icon.svg --export-type=png --export-filename=icon16.png --export-width=16
inkscape icon.svg --export-type=png --export-filename=icon48.png --export-width=48
inkscape icon.svg --export-type=png --export-filename=icon128.png --export-width=128
```

Sem os PNGs, a extensão funciona, mas o Chrome mostra ícone genérico.
