from fastapi import FastAPI, HTTPException,Depends,status
from pydantic import BaseModel
from typing import List, Annotated,Optional
import models
from database import SessionLocal,engine    
from sqlalchemy.orm import Session
from sqlalchemy import or_
app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# class ChoiceBase(BaseModel) :
#     choice_text: str
#     is_correct: bool

# class QuestionBase(BaseModel):
#     questions_text: str
#     choices: List[ChoiceBase]



# class UserBase(BaseModel):
#     username: str
#     password: str
#     email: str
#     phone: str


# class ProfileBase(BaseModel):
#     profile_image: str



class ProfileBase(BaseModel):
    profile_image: Optional[str] = None

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class Profile(ProfileBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    username: str
    password: str
    email: str
    phone: str

class UserCreate(UserBase):
    profile: Optional[ProfileCreate] = None

class UserUpdate(UserBase):
    profile: Optional[ProfileUpdate] = None

class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    profile: Optional[Profile] = None

    class Config:
        orm_mode = True




def get_db():
    """Get database connection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session,Depends(get_db)]



# @app.post("/questions/")
# async def create_questions(question: QuestionBase, db: db_dependency):
#     db_question = models.Questions(questions_text=question.questions_text)
#     db.commit()
#     # db.refresh(db_question)
#     for choice in question.choices:
#         db_choice = models.Choices(choice_text=choice.choice_text,is_correct=choice.is_correct,question_id=db_question.id)
#         db.add(db_choice)
#     db.commit()
#     return db_question


@app.post("/users/", response_model=User)
def create_user(user: UserCreate,db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if email or phone already exists
    existing_user = db.query(models.User).filter(or_(models.User.email == user.email, models.User.phone == user.phone)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or phone already exists")
    profile_data = user.profile
    user_data = user.dict(exclude={"profile"})
    db_user = models.User(**user_data)
    if profile_data:
        db_profile = models.Profile(**profile_data.dict())
        db_user.profile = db_profile

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return HTTPException(status_code=status.HTTP_201_CREATED, detail="User created successfully")



@app.get("/users/", response_model=List[User])
def list_user(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all users"""
    return db.query(models.User).offset(skip).limit(limit).all()


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a single user"""
    return db.query(models.User).filter(models.User.id == user_id).first()


@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user: UserUpdate,db: Session = Depends(get_db)):
    """Update a user"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        user_data = user.dict(exclude_unset=True, exclude={"profile"})
        for field, value in user_data.items():
            setattr(db_user, field, value)
        
        if user.profile:
            if db_user.profile:
                db.query(models.Profile).filter(models.Profile.id == db_user.profile.id).update(user.profile.dict())
            else:
                db_profile = models.Profile(**user.profile.dict())
                db_user.profile = db_profile
        else:
            if db_user.profile:
                db.delete(db_user.profile)
                db_user.profile = None

        db.commit()
        db.refresh(db_user)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return HTTPException(status_code=status.HTTP_200_OK, detail="User updated successfully")


@app.delete("/users/{user_id}")
def delete_user(user_id: int,db: Session = Depends(get_db)):
    """Delete a user"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        if db_user.profile:
            db.delete(db_user.profile)
        db.delete(db_user)
        db.commit()
        return HTTPException(status_code=status.HTTP_200_OK, detail="User deleted successfully")
    else:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")