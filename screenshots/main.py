from fastapi import FastAPI, Query, Response, status
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()
#day1--

@app.get("/")
def home():
    return {"message": "Welcome to LearnHub Online Courses"}
#day 2 endpoint
class EnrollRequest(BaseModel):
    student_name: str = Field(..., min_length=2)
    course_id: int = Field(..., gt=0)
    email: str = Field(..., min_length=5)
    payment_method: str = "card"
    coupon_code: str = ""
    gift_enrollment: bool = False
    recipient_name: str = ""


class NewCourse(BaseModel):
    title: str = Field(..., min_length=2)
    instructor: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    level: str = Field(..., min_length=2)
    price: int = Field(..., ge=0)
    seats_left: int = Field(..., gt=0)

# ── Courses Data (acting as DB)
courses = [
    {"id": 1, "title": "Python Basics", "instructor": "Amit", "category": "Data Science", "level": "Beginner", "price": 0, "seats_left": 10},
    {"id": 2, "title": "Data science", "instructor": "John", "category": "Web Dev", "level": "Intermediate", "price": 1999, "seats_left": 5},
    {"id": 3, "title": "UI Design", "instructor": "Sara", "category": "Design", "level": "Beginner", "price": 999, "seats_left": 8},
    {"id": 4, "title": "Docker & Kubernetes", "instructor": "Mike", "category": "DevOps", "level": "Advanced", "price": 2999, "seats_left": 3},
    {"id": 5, "title": "Machine Learning", "instructor": "Raj", "category": "Data Science", "level": "Advanced", "price": 3999, "seats_left": 6},
    {"id": 6, "title": "Figma Masterclass", "instructor": "Neha", "category": "Design", "level": "Intermediate", "price": 1499, "seats_left": 7},
]
enrollments = []
enrollment_counter = 1
wishlist=[]
@app.get("/courses")
def get_courses():
    total_seats = sum(c["seats_left"] for c in courses)
    return {
        "courses": courses,
        "total": len(courses),
        "total_seats_available": total_seats
    }


@app.get("/courses/summary")
def courses_summary():
    free_courses = [c for c in courses if c["price"] == 0]
    expensive = max(courses, key=lambda c: c["price"])
    total_seats = sum(c["seats_left"] for c in courses)

    category_count = {}
    for c in courses:
        category_count[c["category"]] = category_count.get(c["category"], 0) + 1

    return {
        "total_courses": len(courses),
        "free_courses": len(free_courses),
        "most_expensive": expensive,
        "total_seats": total_seats,
        "category_distribution": category_count
    }

#filter
@app.get("/courses/filter")
def filter_courses(
    category: str = None,
    level: str = None,
    max_price: int = None,
    has_seats: bool = None
):
    result = filter_courses_logic(category, level, max_price, has_seats)
    return {"courses": result, "count": len(result)}



@app.get("/enrollments")
def get_enrollments():
    return {"enrollments": enrollments, "total": len(enrollments)}
    #day 3 

def find_course(course_id: int):
    for c in courses:
        if c["id"] == course_id:
            return c
    return None


def calculate_enrollment_fee(price, seats_left, coupon_code):
    discount = 0

    # Early bird
    if seats_left > 5:
        discount += price * 0.10

    # Coupons
    if coupon_code == "STUDENT20":
        discount += price * 0.20
    elif coupon_code == "FLAT500":
        discount += 500

    final_price = max(0, int(price - discount))
    return final_price, discount


def filter_courses_logic(category=None, level=None, max_price=None, has_seats=None):
    result = courses

    if category is not None:
        result = [c for c in result if c["category"] == category]

    if level is not None:
        result = [c for c in result if c["level"] == level]

    if max_price is not None:
        result = [c for c in result if c["price"] <= max_price]

    if has_seats is not None:
        result = [c for c in result if (c["seats_left"] > 0) == has_seats]

    return result

# Enrollment API

@app.post("/enrollments")
def enroll(data: EnrollRequest):
    global enrollment_counter

    course = find_course(data.course_id)
    if not course:
        return {"error": "Course not found"}

    if course["seats_left"] <= 0:
        return {"error": "No seats available"}

    if data.gift_enrollment and not data.recipient_name:
        return {"error": "Recipient name required for gift"}

    final_fee, discount = calculate_enrollment_fee(
        course["price"], course["seats_left"], data.coupon_code
    )

    course["seats_left"] -= 1

    enrollment = {
        "enrollment_id": enrollment_counter,
        "student": data.student_name,
        "course": course["title"],
        "instructor": course["instructor"],
        "original_price": course["price"],
        "discount": discount,
        "final_fee": final_fee,
        "recipient": data.recipient_name if data.gift_enrollment else None
    }

    enrollments.append(enrollment)
    enrollment_counter += 1

    return {"message": "Enrollment successful", "enrollment": enrollment}

#day 4 crud

@app.post("/courses")
def add_course(new_course: NewCourse, response: Response):
    if any(c["title"].lower() == new_course.title.lower() for c in courses):
        response.status_code = 400
        return {"error": "Course already exists"}

    new_id = max(c["id"] for c in courses) + 1

    course = {"id": new_id, **new_course.dict()}
    courses.append(course)

    response.status_code = 201
    return {"course": course}


@app.put("/courses/{course_id}")
def update_course(course_id: int, price: int = None, seats_left: int = None):
    course = find_course(course_id)
    if not course:
        return {"error": "Course not found"}

    if price is not None:
        course["price"] = price

    if seats_left is not None:
        course["seats_left"] = seats_left

    return {"course": course}


@app.delete("/courses/{course_id}")
def delete_course(course_id: int):
    course = find_course(course_id)
    if not course:
        return {"error": "Course not found"}

    for e in enrollments:
        if e["course"] == course["title"]:
            return {"error": "Cannot delete course with enrollments"}

    courses.remove(course)
    return {"message": "Deleted successfully"}

#wishlist endpoint
@app.post("/wishlist/add")
def add_wishlist(student_name: str, course_id: int):
    course = find_course(course_id)
    if not course:
        return {"error": "Course not found"}

    for w in wishlist:
        if w["student"] == student_name and w["course_id"] == course_id:
            return {"error": "Already in wishlist"}

    wishlist.append({"student": student_name, "course_id": course_id, "price": course["price"]})
    return {"message": "Added to wishlist"}

@app.get("/wishlist")
def view_wishlist():
    total_value = sum(w["price"] for w in wishlist)
    return {"wishlist": wishlist, "total_value": total_value}


@app.delete("/wishlist/remove/{course_id}")
def remove_wishlist(course_id: int, student_name: str):
    for w in wishlist:
        if w["course_id"] == course_id and w["student"] == student_name:
            wishlist.remove(w)
            return {"message": "Removed"}
    return {"error": "Not found"}

@app.post("/wishlist/enroll-all")
def enroll_all(student_name: str, payment_method: str):
    results = []
    total = 0

    for w in wishlist[:]:
        if w["student"] == student_name:
            course = find_course(w["course_id"])
            if course and course["seats_left"] > 0:
                fee, _ = calculate_enrollment_fee(course["price"], course["seats_left"], "")
                total += fee
                results.append(course["title"])
                course["seats_left"] -= 1
                wishlist.remove(w)

    return {"enrolled": results, "total_fee": total}
    #search,sort,pagination
@app.get("/courses/search")
def search_courses(keyword: str):
    result = [
        c for c in courses
        if keyword.lower() in c["title"].lower()
        or keyword.lower() in c["instructor"].lower()
        or keyword.lower() in c["category"].lower()
    ]
    return {"results": result, "total_found": len(result)}


@app.get("/courses/sort")
def sort_courses(sort_by: str = "price"):
    return {"courses": sorted(courses, key=lambda c: c[sort_by])}
@app.get("/courses/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    end = start + limit
    total_pages = (len(courses) + limit - 1) // limit

    return {
        "page": page,
        "total_pages": total_pages,
        "data": courses[start:end]
    }
@app.get("/enrollments/search")
def search_enrollments(student_name: str):
    result = [e for e in enrollments if student_name.lower() in e["student"].lower()]
    return {"results": result}


@app.get("/enrollments/sort")
def sort_enrollments():
    return {"enrollments": sorted(enrollments, key=lambda e: e["final_fee"])}


@app.get("/enrollments/page")
def paginate_enrollments(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    end = start + limit
    return {"data": enrollments[start:end]}
@app.get("/courses/browse")
def browse(
    keyword: str = None,
    category: str = None,
    level: str = None,
    max_price: int = None,
    sort_by: str = "price",
    page: int = 1,
    limit: int = 3
):
    result = courses

    if keyword:
        result = [c for c in result if keyword.lower() in c["title"].lower()]

    if category:
        result = [c for c in result if c["category"] == category]

    if level:
        result = [c for c in result if c["level"] == level]

    if max_price:
        result = [c for c in result if c["price"] <= max_price]

    result = sorted(result, key=lambda c: c[sort_by])

    start = (page - 1) * limit
    end = start + limit

    return {
        "results": result[start:end],
        "total": len(result)
    }
@app.get("/courses/{course_id}")
def get_course(course_id: int):
    for c in courses:
        if c["id"] == course_id:
            return {"course": c}
    return {"error": "Course not found"}