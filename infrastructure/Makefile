.PHONY: help init validate plan apply destroy clean

help:
	@echo "Available commands:"
	@echo "  make init      - Initialize Terraform"
	@echo "  make validate  - Validate Terraform configuration"
	@echo "  make plan      - Show deployment plan"
	@echo "  make apply     - Deploy infrastructure"
	@echo "  make destroy   - Destroy infrastructure"
	@echo "  make clean     - Clean temporary files"

init:
	terraform init

validate:
	terraform validate

plan: validate
	terraform plan -out=tfplan

apply: plan
	terraform apply tfplan

destroy:
	terraform destroy -auto-approve

clean:
	rm -rf .terraform/
	rm -f tfplan
	rm -f *.tfstate*
	rm -f ../lambdas/placeholder.zip