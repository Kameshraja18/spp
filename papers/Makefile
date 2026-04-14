PDF=ieee_draft.pdf
TEX=ieee_draft.tex

all: $(PDF)

$(PDF): $(TEX)
	latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX)

clean:
	latexmk -C

.PHONY: all clean
