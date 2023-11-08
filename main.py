from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import databases
import sqlalchemy
from databases import Database

app = FastAPI()

DATABASE_URL = "postgresql://postgres:12345@localhost/fast_lms"
database = Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("full_name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True, nullable=False),
    sqlalchemy.Column("password", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("phone", sqlalchemy.String, nullable=False),
)

profile = sqlalchemy.Table(
    "profile",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("profile_picture", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("user_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False),
)


class UserCreate(BaseModel):
    first_name: str
    email: str
    password: str
    phone: str


class ProfileCreate(BaseModel):
    profile_picture: str


class User(BaseModel):
    id: int
    first_name: str
    email: str
    phone: str
    profile_picture: str


@app.post("/register/", response_model=UserCreate)
async def register_user(user: UserCreate):

    query = users.select().where(
        (users.c.email == user.email) | (users.c.phone == user.phone)
    )
    existing_user = await database.fetch_one(query)

    if existing_user:
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email already exists")
        else:
            raise HTTPException(status_code=400, detail="Phone already exists")


    query = users.insert().values(
        full_name=user.first_name,
        email=user.email,
        password=user.password,
        phone=user.phone,
    )
    last_record_id = await database.execute(query)

    return {**user.dict(), "id": last_record_id}


@app.post("/create-profile/", response_model=ProfileCreate)
async def create_profile(profile: ProfileCreate):
    query = profile.insert().values(
        profile_picture=profile.profile_picture,
        user_id=profile.user_id,
    )
    last_record_id = await database.execute(query)
    return {**profile.dict(), "id": last_record_id}


@app.get("/user/{user_id}", response_model=User)
async def get_user(user_id: int):
    # Query user details and their profile using user_id as a foreign key
    query = users.select().where(users.c.id == user_id)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile_query = profile.select().where(profile.c.user_id == user_id)
    profile_data = await database.fetch_one(profile_query)

    return User(
        id=user["id"],
        first_name=user["full_name"],
        email=user["email"],
        phone=user["phone"],
        profile_picture=profile_data["profile_picture"] if profile_data else None,
    )


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
