[docs.md](https://github.com/user-attachments/files/33100394/docs.md)
  
**WORK-IN-PROGRESS DOCUMENTATION**  
**Adaptive Classroom Noise Monitoring and Warning System Using AIoT**  
**Project Status: WORK IN PROGRESS / NOT YET FINAL**

**1\. Current Project Status**

This is not the finished AIoT system. It is the current dashboard/prototype version of the project. The dashboard now reads actual backend responses and reports missing data explicitly; see [dashboard/README.md](dashboard/README.md) for its API usage and UI states. The complete physical AIoT system is still being developed.
The documentation therefore records what is currently available and what still needs to be completed  
.  
**2\. What Is Currently Available in our System**

* SONIQ classroom monitoring dashboard with Live and History views.
* Backend health and warning-configuration readiness from `GET /health`.
* Actual event-history display when `GET /api/v1/events` is available. The current backend does not implement this route, so the dashboard reports it as Unavailable.
* Classification of a user-selected WAV through `POST /api/v1/classify`.
* Explicit Loading, Empty, Error, Unavailable, Stale, Success, and Unknown states.
* Sensor/device status reported by actual backend events, without claiming physical verification.
* CSV export of actual loaded events.
* Responsive layout, accessible keyboard navigation, and VS Code launch configuration.
* A separate local backend contract-check panel with an explicitly simulated warning case.


**3\. What Is Not Finished Yet**

* Actual ESP32 integration.  
* Actual microphone sensor integration.  
* Real classroom noise readings.  
* Physical buzzer control.  
* Physical LED warning control.  
* Real alert-delay testing using the hardware.  
* Continuous classroom hardware testing.  
* Complete teacher authentication and authorization.  
* Complete Wi-Fi/network security implementation.  
* Actual persistent database/history for the deployed system.  
* Final AI/ML implementation, if required by the final design.

**4\. Progress of the System**

We did not mark unfinished features as PASS. We should prepare the test cases, test the parts that are already available, record problems, and test each new feature after the development team completes it.

| Test Area	 | Current Status | What Should Do | Final Status  |
| :---- | :---- | :---- | :---- |
| Dashboard  | Available | Test buttons, navigation, classroom selection and displays. | To Test  |
| Noise monitoring  | Not finished  | Test real microphone readings when connected.  | Pending  |
| Buzzer   | Not finished  | Test activation above threshold and no activation below threshold.  | Pending  |
| LEDs  | Not finished  | Check normal/warning indicators.  | Pending  |
| Discussion Mode   | Prototype | Verify final threshold after hardware integration.  | Pending  |
| Group Activity Mode  | Prototype | Verify final threshold after hardware integration.  | Pending  |
| Alert delay  | Not finished  | Measure whether warning activates only after required delay.  | Pending  |
| History  | Prototype | Retest with real stored readings.  | Pending  |
| Report | Prototype | Verify exported report after real data is available.  | Pending  |
| Security  | Not finished  | Test teacher-only settings and protected credentials. | Pending  |

**5\. QA Testing Checklist**

☐ Dashboard features tested  
☐ Microphone detects classroom noise  
☐ Buzzer activates above the threshold  
☐ Buzzer remains off within the allowed level  
☐ Discussion Mode uses the correct threshold  
☐ Group Activity Mode uses the correct threshold  
☐ LEDs display the correct warning  
☐ Alert delay works correctly  
☐ System operates continuously  
☐ Real readings appear on the dashboard  
☐ History saves real readings  
☐ Report contains correct real data  
☐ Teacher-only controls are protected  
☐ Wi-Fi credentials are protected

**6\. Testing Record Format**

Every completed test should be recorded using the following format:  
Test ID:  
Date:  
Tester:  
Feature Tested:  
Expected Result:  
Actual Result:  
Problem Encountered:  
Solution:  
Retest Result:  
Status: PASS / FAIL / NEEDS IMPROVEMENT

**7\. Security Responsibilities**

* Check that only the teacher or authorized user can change classroom modes.  
* Check that unauthorized users cannot change noise thresholds.  
* Keep Wi-Fi credentials out of public/client-side code.  
* Protect any account or device credentials.  
* Avoid collecting unnecessary student personal information.  
* Validate sensor data before using it in the system.  
* Protect exported reports from unauthorized access.

**8\. Documentation Responsibilities**

* Materials list – record every component used.  
* System description – explain how the final system works.  
* Hardware documentation – record ESP32, microphone, buzzer, LEDs, wiring, and power connections.  
* Testing results – record every completed test.  
* Problems encountered – record bugs and hardware/software issues.  
* Solutions – record how each problem was fixed.  
* System updates – record changes made by the team.  
* User manual – explain how the teacher operates the finished system.  
* Screenshots/photos – keep evidence of development and testing.

9\. Current Prototype Notes From the System

* The dashboard overview displays only actual backend responses. It does not simulate readings, warning decisions, thresholds, or event history.
* The local integration-check panel contains an explicitly simulated warning-policy case; that result is never shown as live dashboard data.
* The current backend does not implement `GET /api/v1/events`, so event history is reported as Unavailable rather than as an empty history.
* `POST /api/v1/classify` returns a classification only; it does not provide a sound level or evaluate warning policy.
* Sensor status reported in an event is device-reported status, not proof of a physically connected sensor.
* Warning policy and thresholds are owned by the backend and are never computed by the dashboard.

