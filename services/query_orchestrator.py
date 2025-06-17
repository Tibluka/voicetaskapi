from spending_service import SpendingService
from profile_config_service import ProfileConfigService

class QueryOrchestrator:
    def __init__(self, db, user_id: str):
        self.user_id = user_id
        self.spending_service = SpendingService(db, user_id)
        self.profile_config_service = ProfileConfigService(db, user_id)

    async def execute_queries(self, query_instructions: dict) -> dict:
        """
        Recebe o JSON com instruções da IA (ex: { collection: 'spendings', filters: {...} })
        e executa as consultas necessárias.

        Se mais de uma coleção for necessária, ele lida com isso aqui.
        """
        collections = query_instructions.get("collections", [])
        result = {}

        for collection in collections:
            if collection["name"] == "spendings":
                spendings = await self.spending_service.get_spendings(collection.get("filters", {}))
                result["spendings"] = spendings

            elif collection["name"] == "profile_config":
                config = await self.profile_config_service.get_config()
                result["profile_config"] = config

        return result