import asyncio
from neo4j import AsyncGraphDatabase

async def check():
    driver = AsyncGraphDatabase.driver("bolt://cv-neo4j:7687", auth=("neo4j", "password"))
    async with driver.session() as s:
        r = await s.run("MATCH (a:Asset) RETURN DISTINCT a.organization_id as org, count(a) as cnt ORDER BY cnt DESC")
        rows = await r.data()
        for row in rows:
            print(row)
    await driver.close()

asyncio.run(check())
