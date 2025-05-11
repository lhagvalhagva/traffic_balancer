"use client";

import Image from "next/image";
import UserMenu from '@/components/UserMenu';


type HeaderProps = {
  isConnected: boolean;
  onToggleSidebar?: () => void; // Optional function to toggle sidebar
};

export default function Header({ isConnected, onToggleSidebar }: HeaderProps) {
  return (
    <header className="bg-blue-700 text-white shadow-md">
      {/* New Row for Status and Navigation */}
      <div className="bg-white text-blue-700 p-4 flex justify-between items-center">
        {/* Status message */}
        <div className="text-sm">
          {isConnected ? "Серверт холбогдсон" : "Серверт холбогдоогүй..."}
        </div>

        {/* Navigation links and information icon */}
        <nav className="flex space-x-6 items-center">
          <a
            href="/help"
            className="text-blue-700 font-bold hover:text-blue-500"
          >
            Тусламж
          </a>
          <a
            href="/contact"
            className="text-blue-700 font-bold hover:text-blue-500"
          >
            Холбоо барих
          </a>
          <a
            href="/feedback"
            className="text-blue-700 font-bold hover:text-blue-500"
          >
            Санал сэтгэгдэл
          </a>

          {/* Information Icon */}
          <div className="ml-4">
            <Image
              src="/images/information.svg"
              alt="Information Icon"
              width={20}
              height={20}
              className="text-blue-700"
            />
          </div>
        </nav>
      </div>

      {/* Main Header Content */}
      {/* Main Header Content */}
      <div className="flex items-center justify-between p-4">
        {/* Left group: Menu + Logo + Description */}
        <div className="flex items-center space-x-4">
          <button onClick={onToggleSidebar}>
            <Image src="/images/menu.svg" alt="Menu Icon" width={24} height={24} />
          </button>
          <div className="flex ">
            <span className="text-2xl font-bold pr-4">traff8x</span>
            <span className="text-sm text-blue-200 leading-tight">
              Авто замын хөдөлгөөний <br />
              нэгдсэн хяналтын систем
            </span>
          </div>
        </div>

        {/* Right group: User button + Icons */}
        <div className="flex items-center space-x-4">
          <button className="text-sm text-white bg-blue-600 hover:bg-blue-500 p-2 rounded-lg">
            ЭТИ 64007: Уран Нямбаатар
          </button>
          <div className="flex space-x-2">
            <button className="p-2 text-white bg-transparent border border-white rounded-full">
              <Image
                src="/images/notification.svg"
                alt="Notification Icon"
                width={24}
                height={24}
              />
            </button>
            <button className="p-2 text-white bg-transparent border border-white rounded-full">
              <Image
                src="/images/dashboard.png"
                alt="Dashboard Icon"
                width={24}
                height={24}
              />
            </button>
            <UserMenu />

          </div>
        </div>
      </div>
    </header>
  );
}
