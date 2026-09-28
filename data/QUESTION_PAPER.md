# Python Programming — Core Concepts
**Total: 37 marks · Answer all questions · Write the question number (Q1, Q2 …) before each answer**

| Q | Question | Marks |
|---|---|---|
| Q1 | What is the difference between a **list** and a **tuple** in Python? Give one example of each. | 4 |
| Q2 | Explain **mutable** and **immutable** objects in Python with an example. **Draw a diagram** showing what happens in memory when you run: `a = [1, 2]; b = a; b.append(3)` | 5 |
| Q3 | What is a **decorator** in Python? Write a simple decorator that prints `Start` before and `End` after a function runs. | 5 |
| Q4 | What is a **generator** in Python? How is it different from a normal function that returns a list? | 4 |
| Q5 | Explain **exception handling** in Python using `try`, `except`, `else` and `finally`, with an example. | 5 |
| Q6 | Write a **list comprehension** that creates a list of the squares of all even numbers from 1 to 10. What is the output? | 3 |
| Q7 | Explain **inheritance** and **method overriding** in Python with a suitable example. | 6 |
| Q8 | What is the difference between `==` and `is` in Python? | 5 |

---

## Answer key (short version, full rubric in `rubrics/python_rubric.json`)

**Q1.** List = mutable, `[1, 2, 3]`. Tuple = immutable, `(3, 4)`. Tuples are hashable (can be dict keys), faster, use less memory, and suit fixed data.

**Q2.** Mutable (list/dict/set) = can change in place. Immutable (int/str/tuple) = a change creates a new object. `b = a` does not copy: both names point to the **same** list, so after `b.append(3)` `a` is also `[1, 2, 3]`.
Diagram: `a ─┐` and `b ─┘` both pointing to `[1, 2, 3]`.

**Q3.** A decorator is a function that takes a function, wraps it to add behaviour, and returns the wrapper. It is applied with `@`.
```python
def log(func):
    def wrapper(*args, **kwargs):
        print("Start")
        result = func(*args, **kwargs)
        print("End")
        return result
    return wrapper
```

**Q4.** A generator uses `yield` and produces values lazily, one at a time. It pauses and resumes its state, does not store all values in memory, and can be iterated only once. A function returning a list builds everything in memory at once.

**Q5.** `try` holds risky code. `except` handles the error. `else` runs only if there was no error. `finally` always runs (cleanup).

**Q6.** `[x**2 for x in range(1, 11) if x % 2 == 0]` gives `[4, 16, 36, 64, 100]`

**Q7.** Inheritance: a child class gets the parent's attributes and methods (code reuse), written `class Dog(Animal)`. Overriding: the child redefines a method with the same name, and `super()` calls the parent's version. Example: `Animal.speak` vs `Dog.speak`, where `Dog().speak()` prints "Dog barks".

**Q8.** `==` compares values. `is` compares identity (same object, same `id()`). `[1,2] == [1,2]` is True, but `[1,2] is [1,2]` is False. Use `is` for `None`.

---

## How to write the test sheets (so every pipeline feature gets tested)

Use plain A4 paper and a dark pen. Photograph each page flat, in good light, straight from above (or scan it). Save them in `Ai_Project_Test\data\samples\` as `page1.jpg`, `page2.jpg` … or as one PDF.

Write the answers in a **mix of qualities** on purpose:

| Q | Write it like this | Tests |
|---|---|---|
| Q1 | Fully correct, neat | High score, **high** confidence |
| Q2 | Correct text **plus a hand-drawn arrow diagram** in the middle, then continue writing below it | Diagram interrupts the text |
| Q3 | Correct, but **start near the bottom of a page and continue on the next page** (no "Q3" on the new page) | Answer spills across pages |
| Q4 | Correct meaning in **your own words** (don't copy the key, e.g. "it gives one item at a time using yield, saves RAM") | Scoring on meaning, not keywords |
| Q5 | **Cross out** one wrong line (strike it through), then write the correct one | Crossed-out lines ignored |
| Q6 | Code with a **mistake**, e.g. output `[1, 4, 9, 16 …]` (all numbers, not even ones) | Partial marks |
| Q7 | **Half-wrong**: explain inheritance, skip overriding, no example | Low score |
| Q8 | **Messy/fast handwriting**, plus a small margin note | **Low** confidence, flagged for human review |

2–4 pages in total is ideal.
