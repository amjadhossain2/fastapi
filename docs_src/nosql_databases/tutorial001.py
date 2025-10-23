from contextlib import asynccontextmanager
from typing import List, Optional

from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field

# MongoDB connection settings
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "heroesdb"


class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(ObjectId),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )


class Hero(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    age: Optional[int] = None
    secret_name: str


class HeroUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    secret_name: Optional[str] = None


# MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(MONGODB_URL)
    yield
    # Shutdown
    if mongodb_client:
        mongodb_client.close()


def get_database():
    if mongodb_client is None:
        raise RuntimeError("Database not initialized")
    return mongodb_client[DATABASE_NAME]


def get_collection():
    database = get_database()
    return database["heroes"]


app = FastAPI(lifespan=lifespan)


@app.post("/heroes/", response_model=Hero)
async def create_hero(hero: Hero, collection=Depends(get_collection)):
    hero_dict = hero.model_dump(by_alias=True, exclude={"id"})
    result = await collection.insert_one(hero_dict)
    hero_dict["_id"] = result.inserted_id
    return Hero(**hero_dict)


@app.get("/heroes/", response_model=List[Hero])
async def read_heroes(
    collection=Depends(get_collection),
    skip: int = 0,
    limit: int = Query(default=100, le=100),
):
    heroes = []
    cursor = collection.find().skip(skip).limit(limit)
    async for document in cursor:
        heroes.append(Hero(**document))
    return heroes


@app.get("/heroes/{hero_id}", response_model=Hero)
async def read_hero(hero_id: str, collection=Depends(get_collection)):
    try:
        object_id = ObjectId(hero_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid hero ID format") from None

    hero = await collection.find_one({"_id": object_id})
    if hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")
    return Hero(**hero)


@app.patch("/heroes/{hero_id}", response_model=Hero)
async def update_hero(hero_id: str, hero: HeroUpdate, collection=Depends(get_collection)):
    try:
        object_id = ObjectId(hero_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid hero ID format") from None

    hero_dict = hero.model_dump(exclude_unset=True)
    if len(hero_dict) >= 1:
        result = await collection.update_one(
            {"_id": object_id}, {"$set": hero_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Hero not found")

    updated_hero = await collection.find_one({"_id": object_id})
    if updated_hero is None:
        raise HTTPException(status_code=404, detail="Hero not found")
    return Hero(**updated_hero)


@app.delete("/heroes/{hero_id}")
async def delete_hero(hero_id: str, collection=Depends(get_collection)):
    try:
        object_id = ObjectId(hero_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid hero ID format") from None

    result = await collection.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hero not found")
    return {"ok": True}
