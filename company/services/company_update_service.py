from company.repositories.company_repository import CompanyRepository


class CompanyUpdateService:
    def __init__(self, repository=None):
        self.repository = repository or CompanyRepository()

    def execute(self, company, validated_data: dict, actor=None):
        return self.repository.update_company(
            company=company,
            update_data=validated_data,
            actor=actor,
        )
