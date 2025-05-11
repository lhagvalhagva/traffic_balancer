import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { useAuth } from '@/lib/AuthContext'; // Assuming it's correctly set up in the context

export default function UserMenu() {
    const [showMenu, setShowMenu] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const { logout } = useAuth(); // Destructure `logout` from useAuth

    // Hide menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowMenu(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setShowMenu((prev) => !prev)}
                className="p-2 text-white bg-transparent border border-white rounded-full"
            >
                <Image src="/images/user.png" alt="User Icon" width={24} height={24} />
            </button>
            {showMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white text-gray-800 shadow-lg rounded-md overflow-hidden z-50">
                    <button className="w-full text-left px-4 py-2 hover:bg-gray-100">
                        Хэрэглэгчийн мэдээлэл
                    </button>
                    <button className="w-full text-left px-4 py-2 hover:bg-gray-100">
                        Бүртгэл засах
                    </button>
                    <button
                        onClick={logout} // Call logout when this button is clicked
                        className="w-full text-left px-4 py-2 hover:bg-gray-100"
                    >
                        Гарах
                    </button>
                </div>
            )}
        </div>
    );
}
