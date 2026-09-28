# Makefile — dotlib
.PHONY: check palettes hooks
check:
	@sh test/contract.sh && sh test/onglets.sh && sh test/anti-fuite.sh
palettes:
	@bin/palettes-tsv > share/palettes.tsv
hooks:
	@cp bin/hooks/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push && echo "crochet pre-push installé"
