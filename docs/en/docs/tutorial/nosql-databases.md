# NoSQL (Distributed) Databases { #nosql-distributed-databases }

**FastAPI** doesn't require you to use a NoSQL database. But you can use **any NoSQL database** that you want.

Here we'll see an example using <a href="https://www.mongodb.com/" class="external-link" target="_blank">MongoDB</a>.

You could adapt this to any other NoSQL database like:

* <a href="https://couchbase.com/" class="external-link" target="_blank">Couchbase</a>
* <a href="https://aws.amazon.com/dynamodb/" class="external-link" target="_blank">Amazon DynamoDB</a>
* <a href="https://cassandra.apache.org/" class="external-link" target="_blank">Cassandra</a>
* etc.

/// tip

There is also a tutorial using a [SQL database](./sql-databases.md){.internal-link target=_blank}.

///

## Import and Set Up MongoDB

We'll use <a href="https://motor.readthedocs.io/" class="external-link" target="_blank">Motor</a>, an async Python driver for MongoDB that is compatible with FastAPI's async capabilities.

First, make sure you create your [virtual environment](../virtual-environments.md){.internal-link target=_blank}, activate it, and install `motor`:

<div class="termy">

```console
$ pip install motor

---> 100%
```

</div>

### MongoDB Connection

Create a MongoDB connection URL and database name:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[11:12] hl[11:12] *}

The connection URL format is:

* For local MongoDB: `mongodb://localhost:27017`
* For MongoDB Atlas (cloud): `mongodb+srv://username:password@cluster.mongodb.net/`

## Create Pydantic Models

### MongoDB ObjectId Handler

MongoDB uses `ObjectId` as the default type for document IDs. We need to create a custom Pydantic type to handle this:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[15:33] hl[15:33] *}

This `PyObjectId` class allows Pydantic to work with MongoDB's `ObjectId` type.

### Hero Model

Create the `Hero` model:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[36:51] hl[36:51] *}

The `Hero` model uses:

* `model_config` with `populate_by_name=True` to allow using `_id` or `id`
* `arbitrary_types_allowed=True` to work with MongoDB's `ObjectId`
* `Field(alias="_id")` to map the Pydantic `id` field to MongoDB's `_id` field

We also create a `HeroUpdate` model for partial updates with all optional fields.

## Create the MongoDB Client

Motor's `AsyncIOMotorClient` manages connections to MongoDB:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[54:55] hl[54:55] *}

## Create Dependencies

Create functions to get the database and collection:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[58:68] hl[58:68] *}

We create a `CollectionDep` dependency that will be used in our path operations.

## Create the App and Initialize MongoDB

Create the FastAPI app and set up a lifespan context manager to connect and disconnect from MongoDB:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[58:67] hl[58:67] *}

The lifespan context manager creates the MongoDB client when the application starts and closes the connection when the application shuts down.

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[80:80] hl[80] *}

## Create a Hero

Create a path operation to create a hero:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[83:89] hl[83:89] *}

We exclude the `id` field when inserting, as MongoDB will generate the `_id` automatically.

## Read Heroes

Read heroes with pagination:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[92:102] hl[92:102] *}

MongoDB's `find()` returns a cursor that we can iterate over asynchronously.

## Read a Single Hero

Read a single hero by ID:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[105:115] hl[105:115] *}

We convert the string `hero_id` to an `ObjectId` and handle any conversion errors.

## Update a Hero

Update a hero's data using the `HeroUpdate` model for partial updates:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[118:134] hl[118:134] *}

We use MongoDB's `$set` operator to update only the provided fields.

## Delete a Hero

Delete a hero:

{* ../../docs_src/nosql_databases/tutorial001_an_py310.py ln[137:147] hl[137:147] *}

## Run the Application

You can run the application with:

<div class="termy">

```console
$ fastapi dev main.py

<span style="color: green;">INFO</span>:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

</div>

/// note

Before running the application, make sure you have MongoDB running. You can:

* Install MongoDB locally: <a href="https://www.mongodb.com/docs/manual/installation/" class="external-link" target="_blank">Installation Guide</a>
* Use MongoDB Atlas (cloud): <a href="https://www.mongodb.com/cloud/atlas" class="external-link" target="_blank">MongoDB Atlas</a>
* Use Docker: `docker run -d -p 27017:27017 mongo`

///

Then go to the `/docs` UI at <a href="http://127.0.0.1:8000/docs" class="external-link" target="_blank">http://127.0.0.1:8000/docs</a>.

You will see the automatic interactive API documentation:

* Create heroes
* Read all heroes
* Read a single hero
* Update heroes
* Delete heroes

## Recap

You can use **any NoSQL database** with **FastAPI**. In this example, we used **MongoDB** with the **Motor** async driver.

The key points are:

* Use async database drivers when possible (like Motor for MongoDB)
* Handle database-specific types (like ObjectId) with custom Pydantic validators
* Use dependency injection to provide database connections to path operations
* Use lifecycle events (`startup` and `shutdown`) to manage database connections

/// tip

You can adapt this pattern to work with other NoSQL databases like Couchbase, DynamoDB, or Cassandra by using their respective async Python drivers.

///
