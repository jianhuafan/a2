
# (C) CS 4410 Spring 2019 Staff, Cornell University
# All rights reserved

from rvr_sync_wrapper import MP, MPthread, MPcondition
import signal

signal.signal(signal.SIGINT, signal.SIG_DFL)

FACILITY_CAPACITY = 15

#    Complete the implementation of the Admitter monitor below using
#    MP Condition variables.

################################################################################
## DO NOT WRITE OR MODIFY ANY CODE ABOVE THIS LINE #############################
################################################################################


class Admitter(MP):
    """ You are in charge of the admission line into the Cornell Career Fair.

    The career fair is being held in Barton Hall which has a max capacity
    specified by FACILITY_CAPACITY. It is your job to manage admissions into
    the career fair.

    We will assume that the fair is attended by people who fall under 1 of
    4 categories: CS students, Econ students, AEM students, and Recruiters.

    CS students filled up the last career fair, so there is a new rule limiting
    their entry. Econ and AEM students tend to compete for the same jobs and are
    known to cut each other in line. In response, Cornell has decided AEM students
    and Econ students can't be in the career fair at the same time.

    Finally, recruiters sometimes run behind schedule and show up at Barton
    after the event begins. They should be allowed into the facility ahead of
    students.

    More technically, the rules for admission are:

    1) There are no more than FACILITY_CAPACITY people allowed in the Career Fair
        at any given time (total includes both students and recruiters).
    2) A CS student will not be allowed to take a enter if - after doing so -
        more than 60% of the people in the Career Fair are CS majors.
    3) An Econ student will not be allowed to enter if there are any AEM majors
        currently in the Career Fair.
    4) Similarly, an AEM Major will not be allowed to enter if there are any
        Econ majors currently in the Career Fair.
    5) Recruiters are always allowed priority access to the Career Fair, subject
        to condition 1. No student should be allowed to enter the Career Fair if
        a Recruiter is waiting.
    """

    def __init__(self, n):
        MP.__init__(self)
        # TODO implement me
        # counter
        self.total = self.Shared("total", 0)
        self.cs_count = self.Shared("cs student", 0)
        self.econ_count = self.Shared("econ student", 0)
        self.aem_count = self.Shared("aem student", 0)
        self.wait_hr_count = self.Shared("waiting recruiter", 0)

        # lock
        self.lock = self.Lock("career fair")
        self.wait_hr_lock = self.Lock("waiting recruiter counter lock")

        # condition variable
        self.empty_cv = self.lock.Condition("career fair not empty")
        self.cs_cv = self.lock.Condition("cs student can enter career fair")
        self.econ_cv = self.lock.Condition("econ student can enter career fair")
        self.aem_cv = self.lock.Condition("aem student can enter career fair")
        self.hr_cv = self.lock.Condition("recruiter waits outside career fair")

    def cs_student_enter(self):
        # TODO implement me
        with self.lock:
            while self.total.read() >= FACILITY_CAPACITY or self.cs_count.read() > self.total.read() * 0.6 or self.wait_hr_count.read() > 0:
                if self.total.read() >= FACILITY_CAPACITY:
                    self.empty_cv.wait()
                if self.cs_count.read() > self.total.read() * 0.6:
                    self.cs_cv.wait()
                if self.wait_hr_count.read() > 0:
                    self.hr_cv.wait()
            self.total.inc()
            self.cs_count.inc()

    def cs_student_leave(self):
        # TODO implement me
        with self.lock:
            self.cs_count.dec()
            self.total.dec()
            self.cs_cv.broadcast()
            self.empty_cv.broadcast()

    def econ_student_enter(self):
        # TODO implement me
        with self.lock:
            while self.total.read() >= FACILITY_CAPACITY or self.aem_count.read() > 0 or self.wait_hr_count.read() > 0:
                if self.total.read() >= FACILITY_CAPACITY:
                    self.empty_cv.wait()
                if self.aem_count.read() > 0:
                    self.econ_cv.wait()
                if self.wait_hr_count.read() > 0:
                    self.hr_cv.wait()
            self.econ_count.inc()
            self.total.inc()

    def econ_student_leave(self):
        # TODO implement me
        with self.lock:
            self.econ_count.dec()
            self.total.dec()
            if self.econ_count.read() == 0:
                self.aem_cv.broadcast()
            self.empty_cv.broadcast()

    def aem_student_enter(self):
        # TODO implement me
        with self.lock:
            while self.total.read() >= FACILITY_CAPACITY or self.econ_count.read() > 0 or self.wait_hr_count.read() > 0:
                if self.total.read() >= FACILITY_CAPACITY:
                    self.empty_cv.wait()
                if self.econ_count.read() > 0:
                    self.aem_cv.wait()
                if self.wait_hr_count.read() > 0:
                    self.hr_cv.wait()
            self.aem_count.inc()
            self.total.inc()

    def aem_student_leave(self):
        # TODO implement me
        with self.lock:
            self.aem_count.dec()
            self.total.dec()
            if self.aem_count.read() == 0:
                self.econ_cv.broadcast()
            self.empty_cv.broadcast()

    def recruiter_enter(self):
        # TODO implement me
        with self.wait_hr_lock:
            self.wait_hr_count.inc()
        with self.lock:
            while self.total.read() >= FACILITY_CAPACITY:
                self.empty_cv.wait()
            self.total.inc()
            with self.wait_hr_lock:
                self.wait_hr_count.dec()

    def recruiter_leave(self):
        # TODO implement me
        with self.lock:
            self.total.dec()
            self.hr_cv.broadcast()
            self.empty_cv.broadcast()



################################################################################
## DO NOT WRITE OR MODIFY ANY CODE BELOW THIS LINE #############################
################################################################################

CS_STUDENT = 0
ECON_STUDENT = 1
AEM_STUDENT = 2
RECRUITER = 3


class Attendee(MPthread):
    def __init__(self, attendee_type, admitter, name):
        MPthread.__init__(self, admitter, name)
        self.attendee_type = attendee_type
        self.admitter = admitter

    def run(self):
        enter_funcs = [
            self.admitter.cs_student_enter,
            self.admitter.econ_student_enter,
            self.admitter.aem_student_enter,
            self.admitter.recruiter_enter
        ]
        leave_funcs = [
            self.admitter.cs_student_leave,
            self.admitter.econ_student_leave,
            self.admitter.aem_student_leave,
            self.admitter.recruiter_leave
        ]
        names = [
            'CsStudent',
            'EconStudent',
            'AemStudent',
            'Recruiter'
        ]

        print('{} trying to enter the career fair'.format(names[self.attendee_type]))
        enter_funcs[self.attendee_type]()
        print('{} has entered the career fair'.format(names[self.attendee_type]))
        self.delay(0.1)
        print('{} leaving the career fair'.format(names[self.attendee_type]))
        leave_funcs[self.attendee_type]()
        print('{} has left'.format(names[self.attendee_type]))


if __name__ == '__main__':

    attendee_counts = [20, 35, 30, 6]
    admitter = Admitter(FACILITY_CAPACITY)

    for attendee_type in [CS_STUDENT, ECON_STUDENT, AEM_STUDENT, RECRUITER]:
        for i in range(attendee_counts[attendee_type]):
            if attendee_type == CS_STUDENT:
                Attendee(attendee_type, admitter, 'CS_STUDENT {}'.format(i)).start()
            elif attendee_type == ECON_STUDENT:
                Attendee(attendee_type, admitter, 'ECON_STUDENT {}'.format(i)).start()
            elif attendee_type == AEM_STUDENT:
                Attendee(attendee_type, admitter, 'AEM_STUDENT {}'.format(i)).start()
            elif attendee_type == RECRUITER:
                Attendee(attendee_type, admitter, 'RECRUITER {}'.format(i)).start()

    admitter.Ready()
