#!/usr/bin/env bash
# Link checker for runcrux.io deploy pipeline
# PLAN-328: Fail deploy if broken links detected

set -e

SITE_DIR="${1:-/home/key/.crux/site/_site}"

if ! command -v htmltest &> /dev/null; then
    echo "Installing htmltest..."
    go install github.com/wjdp/htmltest@latest 2>/dev/null || {
        echo "Warning: htmltest not available, using basic link check"
        # Basic check: find markdown links and verify internal ones exist
        cd "$SITE_DIR"
        broken=0
        while IFS= read -r file; do
            # Extract href values
            grep -oP 'href="[^"]*"' "$file" 2>/dev/null | grep -oP '(?<=href=")[^"]*' | while read -r link; do
                # Skip external links and anchors
                [[ "$link" == http* ]] && continue
                [[ "$link" == "#"* ]] && continue
                [[ "$link" == "mailto:"* ]] && continue
                
                # Check if internal link target exists
                target="${SITE_DIR}${link}"
                target="${target%/}"
                if [[ ! -f "$target" && ! -f "${target}/index.html" && ! -f "${target}.html" ]]; then
                    echo "BROKEN: $link in $file"
                    broken=1
                fi
            done
        done < <(find . -name "*.html" -type f)
        
        if [[ $broken -eq 1 ]]; then
            echo "ERROR: Broken internal links detected"
            exit 1
        fi
        echo "OK: No broken internal links detected"
        exit 0
    }
fi

# Use htmltest if available
cd "$SITE_DIR/.."
cat > .htmltest.yml << 'HTMLTEST'
DirectoryPath: "_site"
CheckExternal: false
CheckInternal: true
IgnoreURLs:
  - "^#"
  - "^mailto:"
HTMLTEST

htmltest
