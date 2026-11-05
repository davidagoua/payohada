# Manuel d'utilisation payohada

Source du manuel utilisateur par rôle, livré en PDF :

- `docs/manuel-utilisation-payohada.pdf` — version finale 1.2 (35 pages, sans la partie administration plateforme) ;
- `docs/manuel-utilisation-payohada.docx` — source éditable.

## Régénérer le manuel

```bash
# 1. Générer le DOCX (python-docx)
/Users/macbookpro/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3 \
  docs/manuel/build_manuel_utilisation.py

# 2. Exporter en PDF (LibreOffice Kit)
NODE="/Applications/DeepSeek Harness.app/Contents/Resources/runtime/primary-runtime/dependencies/node/bin/node"
CLI="/Applications/DeepSeek Harness.app/Contents/Resources/app.asar.unpacked/dsh/node_modules/@deepseek-ai/libreoffice-kit/lib/cli.js"
rm -f docs/manuel-utilisation-payohada.pdf
"$NODE" "$CLI" convert --input docs/manuel-utilisation-payohada.docx \
  --output docs/manuel-utilisation-payohada.pdf
```

Les captures utilisées sont dans `docs/captures/manuel/`. Le script
`build_manuel_utilisation.py` vérifie à la fin le nombre de titres, de tableaux
et d'images du document produit.
