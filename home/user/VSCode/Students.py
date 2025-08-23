import asyncio
import aiosmtplib
from concurrent.futures import ThreadPoolExecutor
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import signal
import sys

# Configuration
STORAGE_FILE_NAME = "students.json"
EMAIL_CONFIG = {
    'sender': 'reports@digitaljournal.com',
    'password': 'your_email_password',
    'smtp_server': 'smtp.example.com',
    'smtp_port': 587,
    'recipient': 'admin@digitaljournal.com'
}

class AsyncRepository:
    def __init__(self, filename: str = STORAGE_FILE_NAME):
        self.filename = filename
        self.students: Dict[int, Dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.running = True
        self._load_lock = asyncio.Lock()
        self._save_lock = asyncio.Lock()
        asyncio.create_task(self._initialize())

    async def _initialize(self):
        await self._ensure_file_exists()
        await self._load_students()
        asyncio.create_task(self._schedule_reports())

    async def _ensure_file_exists(self):
        if not await asyncio.get_event_loop().run_in_executor(
            self._executor, Path(self.filename).exists
        ):
            await self._save_students()

    async def _load_students(self):
        async with self._load_lock:
            try:
                def read_file():
                    with open(self.filename, 'r') as file:
                        return json.load(file)
                
                data = await asyncio.get_event_loop().run_in_executor(
                    self._executor, read_file
                )
                
                # Convert legacy format if needed
                for student_id, student in data.items():
                    if isinstance(student.get('marks'), list) and student['marks'] and isinstance(student['marks'][0], int):
                        student['marks'] = [{
                            'value': mark, 
                            'date': datetime.now().isoformat()
                        } for mark in student['marks']]
                
                self.students = {int(k): v for k, v in data.items()}
            except (json.JSONDecodeError, FileNotFoundError):
                self.students = {}

    async def _save_students(self):
        async with self._save_lock:
            def write_file():
                with open(self.filename, 'w') as file:
                    json.dump(self.students, file, indent=2)
            
            await asyncio.get_event_loop().run_in_executor(
                self._executor, write_file
            )

    async def add_student(self, student: Dict[str, Any]) -> Optional[int]:
        if not student.get('name'):
            return None

        new_id = max(self.students.keys()) + 1 if self.students else 1
        self.students[new_id] = {
            'name': student['name'],
            'marks': student.get('marks', []),
            'info': student.get('info', '')
        }
        await self._save_students()
        return new_id

    async def add_mark(self, id_: int, mark: int) -> bool:
        if id_ not in self.students:
            return False

        mark_data = {
            'value': mark,
            'date': datetime.now().isoformat()
        }

        if 'marks' not in self.students[id_]:
            self.students[id_]['marks'] = []
        
        self.students[id_]['marks'].append(mark_data)
        await self._save_students()
        return True

    async def get_daily_average(self, date: datetime) -> float:
        total = 0
        count = 0
        
        for student in self.students.values():
            for mark in student.get('marks', []):
                try:
                    mark_date = datetime.fromisoformat(mark['date'])
                    if mark_date.date() == date.date():
                        total += mark['value']
                        count += 1
                except (ValueError, KeyError):
                    continue
        
        return round(total / count, 2) if count > 0 else 0.0

    async def _send_email(self, subject: str, body: str):
        try:
            smtp = aiosmtplib.SMTP(
                hostname=EMAIL_CONFIG['smtp_server'],
                port=EMAIL_CONFIG['smtp_port'],
                starttls=True
            )
            await smtp.connect()
            await smtp.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])

            message = f"Subject: {subject}\n\n{body}"
            await smtp.sendmail(EMAIL_CONFIG['sender'], EMAIL_CONFIG['recipient'], message)
            await smtp.quit()
            print(f"Email sent: {subject}")
        except Exception as e:
            print(f"Email sending failed: {e}")

    async def _send_daily_report(self):
        today = datetime.now()
        average = await self.get_daily_average(today)
        subject = f"Daily Average Mark Report - {today.strftime('%Y-%m-%d')}"
        body = f"The average mark for today is: {average}"
        await self._send_email(subject, body)

    async def _send_monthly_report(self):
        today = datetime.now()
        total_students = len(self.students)
        subject = f"Monthly Student Count Report - {today.strftime('%Y-%m')}"
        body = f"The total number of students is: {total_students}"
        await self._send_email(subject, body)

    async def _schedule_reports(self):
        while self.running:
            now = datetime.now()
            # Daily report at 23:55
            daily_report_time = now.replace(hour=23, minute=55, second=0, microsecond=0)
            if now > daily_report_time:
                daily_report_time += timedelta(days=1)
            
            daily_delay = (daily_report_time - now).total_seconds()
            await asyncio.sleep(daily_delay)
            await self._send_daily_report()

            # Monthly report on the 1st of each month at 00:05
            monthly_report_time = now.replace(day=1, hour=0, minute=5, 
                                              second=0, microsecond=0, month=now.month + 1 if now.month < 12 else 1,
                                              year=now.year + 1 if now.month == 12 else now.year)
            if now > monthly_report_time:
                monthly_report_time = monthly_report_time.replace(month=monthly_report_time.month + 1 if monthly_report_time.month < 12 else 1, 
                                                                  year=monthly_report_time.year + 1 if monthly_report_time.month == 12 else monthly_report_time.year)

            monthly_delay = (monthly_report_time - now).total_seconds()
            await asyncio.sleep(monthly_delay)
            await self._send_monthly_report()

    async def shutdown(self):
        self.running = False
        await self._save_students()
        self._executor.shutdown(wait=True)
        print("Repository shutdown complete.")

async def handle_input(repo):
    loop = asyncio.get_event_loop()
    while True:
        def blocking_input():
            return input("Enter command: ")

        command = await loop.run_in_executor(None, blocking_input)

        if command.lower() == 'exit':
            break
        elif command.lower().startswith('add student'):
            try:
                student_data = json.loads(command[len('add student'):].strip())
                student_id = await repo.add_student(student_data)
                if student_id:
                    print(f"Student added with ID: {student_id}")
                else:
                    print("Failed to add student. Ensure the student data is correct.")
            except json.JSONDecodeError:
                print("Invalid JSON format for student data.")
        elif command.lower().startswith('add mark'):
            try:
                parts = command[len('add mark'):].strip().split()
                student_id = int(parts[0])
                mark_value = int(parts[1])
                if await repo.add_mark(student_id, mark_value):
                    print(f"Mark added to student {student_id}")
                else:
                    print(f"Student with ID {student_id} not found.")
            except (ValueError, IndexError):
                print("Invalid format. Use: add mark <student_id> <mark_value>")
        else:
            print("Unknown command.")

async def main():
    repo = AsyncRepository()

    if sys.platform == "win32":
        print("Running on Windows: Using alternative signal handling.")
        async def signal_handler():
            print("Shutting down...")
            await repo.shutdown()
            loop.stop()

        signal.signal(signal.SIGINT, lambda *args: asyncio.create_task(signal_handler()))
    else:
        loop = asyncio.get_event_loop()
        def signal_handler():
            print("Shutting down...")
            asyncio.create_task(repo.shutdown())
            loop.stop()

        loop.add_signal_handler(signal.SIGINT, signal_handler)

    await handle_input(repo)
    await repo.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted.")