import argparse
import logging
from api import start_api_server

# Логгер тохируулах
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("vehicle_counter_api")


def main():
    """
    Тээврийн хэрэгсэл тоолох API серверийг ажиллуулах
    """
    # Аргументийг зохицуулах
    parser = argparse.ArgumentParser(description="Тээврийн хэрэгсэл тоолох API сервер")
    
    parser.add_argument("--host", type=str, default="0.0.0.0",
                       help="Хост нэр эсвэл IP хаяг")
    
    parser.add_argument("--port", type=int, default=8000,
                       help="Порт дугаар")
    
    # Аргументийг задлах
    args = parser.parse_args()
    
    logger.info(f"API сервер эхлүүлж байна {args.host}:{args.port}")
    
    # API сервер эхлүүлэх
    start_api_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main() 