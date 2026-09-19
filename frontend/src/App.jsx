import { useState, useEffect } from 'react'
import UserList from './ContactList'
import './App.css'
import UserForm from './ContactForm'

function App() {
  const [users, setContacts] = useState([])
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentUsers, setCurrentUsers] = useState({})

  useEffect(() => {
    fetchContacts()
  }, [])

  const fetchContacts = async () => {
    const response = await fetch("http://127.0.0.1:5000/users")
    const data = await response.json()
    setContacts(data.users)
    console.log(data.users)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setCurrentUsers({})
  }

  const openCreateModal = () => {
    if (!isModalOpen) setIsModalOpen(true)
  }

  const openEditModal = (users) => {
    if (isModalOpen) return
    setCurrentUsers(users)
    setIsModalOpen(true)
    }

  const onUpdate = () => {
    closeModal()
    fetchContacts()
  }
    return (
    <>
      <UserList users={users} updateUser={openEditModal} updateCallback={onUpdate} />
      <button onClick={openCreateModal}>Create New User</button>
      {isModalOpen && <div className="modal">
        <div className="modal-content">
          <span className="close" onClick={closeModal}>&times;</span>
          <UserForm existinguser={currentUsers} updateCallback={onUpdate}/>
        </div>  
      </div>
      }
    </>
    );
};

export default App
