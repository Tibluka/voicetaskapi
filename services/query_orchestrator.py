from services.spending_service import SpendingService
from services.profile_config_service import ProfileConfigService

class QueryOrchestrator:
    def __init__(self, spendingDB, profileConfigDB, user_id: str):
        self.user_id = user_id
        self.spending_service = SpendingService(spendingDB)
        self.profile_config_service = ProfileConfigService(profileConfigDB)

    def execute_queries(self, query_instructions: dict) -> dict:
        collections_needed = query_instructions.get("collections_needed", [])
        result = {}

        for collection in collections_needed:
            if collection == "spendings":
                spendings = self.spending_service.consult_spending(query_instructions)
                result["spendings"] = spendings

            elif collection == "profile_config":
                config = self.profile_config_service.consult_profile_config(query_instructions)
                result["profile_config"] = config

        return result