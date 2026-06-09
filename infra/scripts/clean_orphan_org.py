"""Remove orphan org nodes from Neo4j."""
import asyncio
from neo4j import AsyncGraphDatabase

ORPHAN_ORG = "3687db64-36e4-417f-b934-2db609c3af34"

async def clean():
    driver = AsyncGraphDatabase.driver("bolt://cv-neo4j:7687", auth=("neo4j", "password"))
    async with driver.session() as s:
        result = await s.run(
            "MATCH (a:Asset) WHERE a.organization_id = $org DETACH DELETE a RETURN count(a) as deleted",
            {"org": ORPHAN_ORG}
        )
        row = await result.single()
        print(f"Deleted {row['deleted']} graph nodes for orphan org {ORPHAN_ORG}")
    await driver.close()

asyncio.run(clean())
