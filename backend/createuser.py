import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from werkzeug.security import generate_password_hash

DB_URL = "sqlite:///instance/mydatabase.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# A classe agora reflete exatamente as colunas do seu banco
class User(Base):
    __tablename__ = "user" 
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String) 

def create_user_db(nome: str, senha: str):
    db = SessionLocal()
    
    try:
        # Busca pelo username
        existing_user = db.query(User).filter(User.username == nome).first()
        if existing_user:
            print(f"❌ O usuário '{nome}' já existe no banco de dados.")
            return

        # Criptografa a senha
        hashed_pw = generate_password_hash(senha)
        
        # Cria o usuário com as chaves corretas: username e password
        new_user = User(username=nome, password=hashed_pw)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ Usuário '{nome}' criado com sucesso! ID: {new_user.id}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao salvar no banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("--- Criação de Usuário (Admin) ---")
    nome_usuario = input("Digite o nome do novo usuário: ")
    senha_usuario = input("Digite a senha: ")
    
    create_user_db(nome_usuario, senha_usuario)