'use client';

import { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface UserType {
    username: string;
    email: string;
    password: string;
    name: string;
}

interface AuthContextType {
    user: UserType | null;
    login: (username: string, password: string) => void;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    login: () => { },
    logout: () => { },
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<UserType | null>(null); // Change to UserType
    const [hasMounted, setHasMounted] = useState(false);
    const router = useRouter();

    // Fake static user
    const fakeUser: UserType = {
        username: 'admin',
        email: 'admin@example.com',
        password: 'admin123',
        name: 'Админ хэрэглэгч',
    };

    const login = (username: string, password: string) => {
        // Check against static credentials
        if (username === fakeUser.username && password === fakeUser.password) {
            setUser(fakeUser);
            localStorage.setItem('user', JSON.stringify(fakeUser)); // Store full user object in localStorage
            router.push('/');
        } else {
            alert('Нэвтрэх нэр эсвэл нууц үг буруу байна!');
        }
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem('user');
        router.push('/login');
    };

    useEffect(() => {
        const savedUser = localStorage.getItem('user');
        try {
            if (savedUser) {
                const parsedUser: UserType = JSON.parse(savedUser);
                setUser(parsedUser);
            }
        } catch (err) {
            // fallback if old format was plain string like "soniy2"
            console.error('Error parsing user from localStorage:', err);
            setUser({ username: savedUser ?? '', email: '', password: '', name: '' });
        }
        setHasMounted(true);
    }, []);

    // Ensure the component only renders after mounted
    if (!hasMounted) return null;

    return (
        <AuthContext.Provider value={{ user, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
