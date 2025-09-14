-include .env

.PHONY: help
help:
	@echo "issue TITLE='...' BODY='...' LABELS='agent,auto'        -> make issue"
	@echo "branch ISSUE=123                                      -> make branch"
	@echo "pr BRANCH=name TITLE='...' BODY='...'                 -> make pr"
	@echo "comments PR=123                                       -> make comments"
	@echo "comment PR=123 BODY='...text...'                      -> make comment"

issue:
	@./issue_create.sh "$(TITLE)" "$(BODY)" "$(LABELS)"

branch:
	@./branch_create.sh "$(ISSUE)" "$(BRANCH)"

pr:
	@./pr_create.sh "$(BRANCH)" "$(TITLE)" "$(BODY)" "$(BASE)"

comments:
	@./pr_fetch_comments.sh "$(PR)"

comment:
	@./pr_comment.sh "$(PR)" "$(BODY)"
