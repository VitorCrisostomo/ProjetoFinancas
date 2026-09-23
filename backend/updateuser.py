from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from werkzeug.security import generate_password_hash

DB_URL = "sqlite:///instance/mydatabase.db"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# A mesma estrutura de classe
class User(Base):
    __tablename__ = "user" 
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String) 

def update_password_db(nome: str, nova_senha: str):
    db = SessionLocal()
    
    try:
        # Busca o usuário pelo username
        user = db.query(User).filter(User.username == nome).first()
        
        if not user:
            print(f"❌ O usuário '{nome}' não foi encontrado no banco de dados.")
            return

        # Criptografa a nova senha
        hashed_pw = generate_password_hash(nova_senha)
        
        # Substitui a senha antiga pela nova
        user.password = hashed_pw
        
        # Salva a alteração
        db.commit()
        
        print(f"✅ Senha do usuário '{nome}' atualizada com sucesso!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao atualizar no banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("--- Recuperação de Senha (Admin) ---")
    nome_usuario = input("Digite o nome do usuário que esqueceu a senha: ")
    nova_senha = input("Digite a nova senha: ")
    
    update_password_db(nome_usuario, nova_senha)