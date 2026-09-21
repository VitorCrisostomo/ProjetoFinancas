import { useState } from "react";
import { createUser, updateUser } from "../../services/userService"; // Importando as funções

const UserForm = ({ existinguser = {}, updateCallback}) => {
    const [firstName, setFirstName] = useState(existinguser.firstName || "");
    const [lastName, setLastName] = useState(existinguser.lastName || "");
    const [email, setEmail] = useState(existinguser.email || "");

    const updating = Object.entries(existinguser).length !== 0;

    const onSubmit = async (e) => {
        e.preventDefault();

        const data = {
            firstName,
            lastName,
            email
        };
        
        try {
            // A lógica de roteamento e métodos HTTP foi movida para api.js
            const response = updating 
                ? await updateUser(existinguser.id, data) 
                : await createUser(data);

            if (response.status !== 201 && response.status !== 200) {
                const message = await response.json();
                alert(message.message);
            } else {
               updateCallback();
            }
        } catch (error) {
            console.error("Erro ao salvar usuário:", error);
            alert("Ocorreu um erro ao processar a requisição.");
        }
    }

    return(
        <form onSubmit={onSubmit}>
            <div>
                <label htmlFor="firstName">First Name:</label>
                <input 
                    type="text" 
                    id="firstName"
                    value={firstName} 
                    onChange={(e) => setFirstName(e.target.value)}
                />
            </div>
            <div>
                <label htmlFor="lastName">Last Name:</label>
                <input 
                    type="text" 
                    id="lastName"
                    value={lastName} 
                    onChange={(e) => setLastName(e.target.value)}
                />
            </div>
            <div>
                <label htmlFor="email">Email:</label>
                <input 
                    type="text" 
                    id="email"
                    value={email} 
                    onChange={(e) => setEmail(e.target.value)}
                />
            </div>
            <button type="submit">{updating ? "Update" : "Create"}</button>
        </form>
    );
};

export default UserForm;