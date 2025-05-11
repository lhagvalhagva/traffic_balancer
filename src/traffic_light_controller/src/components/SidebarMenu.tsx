// components/SidebarMenu.tsx
"use client";

import Image from "next/image";
import { useState, useEffect} from "react";

export default function SidebarMenu() {
    const [selectedMenu, setSelectedMenu] = useState<number | null>(null);
    const [menuItemHeight, setMenuItemHeight] = useState<number>(0);

    const menuItems = [
        { name: "Хянах самбар", icon: "/images/dashboard.svg" },
        { name: "Зохицуулалт", icon: "/images/settings.svg" },
        { name: "Тайлан", icon: "/images/report.svg" },
        { name: "Хүсэлт илгээх", icon: "/images/request.svg" },
    ];

    useEffect(() => {
        // Calculate available height for each menu item
        const headerHeight = document.querySelector("header")?.clientHeight || 0;
        const footerHeight = document.querySelector("footer")?.clientHeight || 0;
        const screenHeight = window.innerHeight;

        // Calculate menu item height (total height minus header and footer height divided by number of items)
        const calculatedHeight = (screenHeight - headerHeight - footerHeight) / menuItems.length;
        setMenuItemHeight(calculatedHeight);
    }, [menuItems.length]);

    return (
        <div className="flex flex-col items-center pt-10">
            {menuItems.map((item, index) => (
                <div
                    key={index}
                    onClick={() => setSelectedMenu(index)}
                    className={`w-full flex items-center justify-center cursor-pointer hover:bg-white hover:text-blue-700 ${selectedMenu === index
                            ? "bg-white text-blue-700"
                            : "border-b border-white"
                        }`}
                    style={{ height: `${menuItemHeight}px` }}
                >
                    <div className="flex flex-col items-center">
                        <Image src={item.icon} alt={item.name} width={24} height={24} />
                        <span className="mt-2">{item.name}</span>
                    </div>
                </div>
            ))}
        </div>
    );
}
