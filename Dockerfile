  # 使用 Python 3.11 官方镜像                               
  FROM python:3.11-slim                                                                                                                       
                                                                                                                                              
  # 设置工作目录                                                                                                                              
  WORKDIR /app                                                                                                                                
                                                                                                                                              
  # 复制依赖文件                                                                                                                              
  COPY requirements.txt .
                                                                                                                                              
  # 安装依赖                                                
  RUN pip install --no-cache-dir -r requirements.txt
                                                                                                                                              
  # 复制应用文件                                                                                                                              
  COPY telegram_claude_bot_advanced.py .                                                                                                      
  COPY .env .                                                                                                                                 
                                                                                                                                              
  # 暴露端口（虽然 Bot 不需要，但 Fly.io 需要）                                                                                               
  EXPOSE 8080                                                                                                                                 
                                                                                                                                              
  # 运行应用                                                                                                                                  
  CMD ["python", "telegram_claude_bot_advanced.py"]
                                                     
