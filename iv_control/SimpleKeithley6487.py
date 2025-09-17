import serial
import time

class SimpleKeithley6487:
    def __init__(self, port='/dev/ttyUSB1', baudrate=9600):
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=5)
        time.sleep(1)
        print(f"连接到 {port}")
    
    def send_command(self, command):
        if not command.endswith('\n'):
            command += '\n'
        self.ser.write(command.encode('ascii'))
        time.sleep(0.1)
    
    def query(self, command):
        self.send_command(command)
        return self.ser.readline().decode('ascii').strip()
    

    def old_setup_for_measurement(self):
        print("设置测量并执行零点校正...")
    
        self.send_command("*RST")                        # 重置仪器
        time.sleep(0.5)
        self.send_command("*CLS")                        # 清除错误
        time.sleep(0.5)
    
        # Step 1: 启用 Zero Check（断开输入）
        self.send_command("SYST:ZCH ON")
        time.sleep(0.3)
    
        # Step 2: 禁用 Zero Correction（必须）
        self.send_command("SYST:ZCOR OFF")              # 注意不是 ZCOR ON
        time.sleep(0.3)
    
        # Step 3: 设置固定电流量程
        self.send_command("SENS:FUNC 'CURR'")
        self.send_command("CURR:RANG 1E-4")              # 例如 200μA 量程
        self.send_command("SENS:CURR:NPLC 1")
        time.sleep(0.3)
    
        # Step 4: 触发一次测量作为“校正值”
        print("触发一次测量以获取零点偏移...")
        self.send_command("INIT")
        time.sleep(0.5)
    
        # Step 5: 采集校正值
        print("采集零点偏移...")
        self.send_command("SYST:ZCOR:ACQ")               # 获取当前偏移值
        self.send_command("SENS:FUNC 'CURR'")
        # 确保Zero Check关闭
        self.send_command("SYST:ZCH OFF")
        time.sleep(0.5)
        
    def setup_for_measurement(self):
        # 重置和清除
        self.send_command("*RST")                        # 重置仪器
        time.sleep(0.5)
        self.send_command("*CLS")                        # 清除错误
        time.sleep(0.5)
        
        # 设置电流测量功能
        self.send_command("SENS:FUNC 'CURR'")           # 设置为电流测量模式
        time.sleep(0.3)
        
        # 设置电流测量参数
        self.send_command("SENS:CURR:RANG 2E-5")        # 设置200nA量程 (修正语法)
        self.send_command("SENS:CURR:NPLC 1")           # 设置积分时间
        time.sleep(0.3)
        
        # Zero Check和Zero Correction设置
        self.send_command("SYST:ZCH ON")                # 启用Zero Check（断开输入进行校零）
        time.sleep(0.5)
        self.send_command("SYST:ZCOR ON")               # 启用Zero Correction（通常应该启用）
        time.sleep(0.3)
        
        # 执行零点校正
        print("执行零点校正...")
        self.send_command("SYST:ZCOR:ACQ")              # 采集零点校正值
        time.sleep(1.0)                                 # 给足够时间完成校正
        
        # 关闭Zero Check，准备正常测量
        self.send_command("SYST:ZCH OFF")               # 关闭Zero Check，连接输入
        time.sleep(0.3)
        
        print("电流测量模式配置完成")
    def read_current(self):
        """读取电流"""
        try:
            response = self.query("READ?")
            if ',' in response:
                current_str = response.split(',')[0].rstrip('A')
                return float(current_str)
            return float(response)                       
        except:
            print(f"读取失败: {response}")
            return None
