// components/SidebarMenu.tsx
"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

export default function SidebarMenu() {
    const pathname = usePathname();
    const router = useRouter();
    const [menuItemHeight, setMenuItemHeight] = useState<number>(0);

    const menuItems = [
        { name: "Хянах самбар", icon: "/images/dashboard.svg", path: "/" },
        { name: "Зохицуулалт", icon: "/images/settings.svg", path: "/settings" },
        { name: "Тайлан", icon: "/images/report.svg", path: "/report" },
        { name: "Хүсэлт илгээх", icon: "/images/request.svg", path: "/request" },
    ];

    useEffect(() => {
        // Calculate available height for each menu item
        const headerHeight = document.querySelector("header")?.clientHeight || 0;
        const screenHeight = window.innerHeight;

        // Calculate menu item height (total height minus header height divided by number of items)
        const calculatedHeight = (screenHeight - headerHeight) / menuItems.length;
        setMenuItemHeight(calculatedHeight);
    }, [menuItems.length]);

    return (
        <div className="flex flex-col items-center pt-10 h-full">
            {menuItems.map((item, index) => {
                const isSelected = pathname === item.path;
                return (
                    <div
                        key={index}
                        onClick={() => router.push(item.path)}
                        className={`w-full flex items-center justify-center cursor-pointer hover:bg-white hover:text-[#2B78E4] relative ${
                            isSelected
                                ? "bg-white text-[#2B78E4] font-semibold"
                                : "text-white"
                        }`}
                        style={{
                            height: `${menuItemHeight}px`,
                            minHeight: '80px'
                        }}
                    >
                        {isSelected && (
                            <div className="absolute left-0 top-0 h-full w-1 bg-white rounded-r"></div>
                        )}
                        <div className="flex flex-col items-center z-10">
                            <Image
                                src={item.icon}
                                alt={item.name}
                                width={24}
                                height={24}
                                className="mb-2 brightness-0 invert"
                            />
                            <span className="text-sm">{item.name}</span>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
