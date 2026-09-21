// src/pages/UsersPage.jsx

import { useState, useEffect } from 'react';
import { fetchUsers } from '../services/userService';
import UserList from '../components/users/UserList'; 
import UserForm from '../components/users/UserForm'; 

export default function UsersPage() {
  const [users, setUsers] = useState([]); 
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState({}); 

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await fetchUsers();
      setUsers(data.users);
      console.log(data.users);
    } catch (error) {
      console.error("Falha ao carregar a lista de usuários:", error);
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setCurrentUser({});
  };

  const openCreateModal = () => {
    if (!isModalOpen) setIsModalOpen(true);
  };

  const openEditModal = (user) => {
    if (isModalOpen) return;
    setCurrentUser(user);
    setIsModalOpen(true);
  };

  const onUpdate = () => {
    closeModal();
    loadUsers(); 
  };

  return (
    <div className="page-container">
      <h2>Gerenciamento de Usuários</h2>
      
      <UserList users={users} updateUser={openEditModal} updateCallback={onUpdate} />
      <button onClick={openCreateModal}>Criar Novo Usuário</button>
      
      {isModalOpen && (
        <div className="modal">
          <div className="modal-content">
            <span className="close" onClick={closeModal}>&times;</span>
            <UserForm existinguser={currentUser} updateCallback={onUpdate} />
          </div>  
        </div>
      )}
    </div>
  );
}