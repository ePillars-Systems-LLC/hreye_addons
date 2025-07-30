/** @odoo-module */

import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl"
import { registry } from "@web/core/registry"
import { Layout } from "@web/search/layout"
import { user } from "@web/core/user"
import { rpc } from "@web/core/network/rpc"
import { AssetsLoadingError, loadBundle, loadJS } from "@web/core/assets"
import { standardActionServiceProps } from "@web/webclient/actions/action_service"

export class HRDashboard extends Component {
  static props = { ...standardActionServiceProps }
  static components = {
    Layout,
  }
  static template = "hr_employee_dashboard.Dashboard"

  setup() {
    // All hooks must be called in the exact same order in every component render
    this.genderChartRef = useRef("gender_chart")
    this.nationalityChartRef = useRef("nationality_chart")
    this.departmentChartRef = useRef("department_chart")
    this.attendanceChartRef = useRef("attendance_chart")
    this.positionChartRef = useRef("position_chart")
    this.monthlyStatsChartRef = useRef("monthly_stats_chart")
    this.contactPopupRef = useRef("contact_popup")

    this.state = useState({
      dash_employee_id: false,
      dash_image: false,
      dash_job_name: false,
      dash_name: false,
      dash_leaves_count: false,
      dash_male_count: false,
      dash_female_count: false,
      dash_top_nationalities_count: false,
      dash_top_nationalities: false,
      // Manager-specific metrics
      manager_leaves_to_approve: false,
      manager_expenses_to_approve: false,
      manager_leaves_approved: false,
      manager_expenses_approved: false,
      manager_total_employees: false,
      manager_employees_checked_in: false,
      manager_employees_absent: false,
      // Employee-specific metrics
      employee_own_leaves_to_approve: false,
      employee_own_expenses_to_approve: false,
      employee_own_leaves_approved: false,
      employee_own_expenses_approved: false,
      employee_own_attendance_status: false,
      employee_own_check_in_time: false,
      employee_own_check_out_time: false,
      dash_leaves_to_approve: false,
      dash_allowcations_to_approve: false,
      dash_expenses_to_approve: false,
      dash_expenses_approved: false,
      dash_age_les_24_m: false,
      dash_age_les_24_f: false,
      dash_age_25_34_m: false,
      dash_age_25_34_f: false,
      dash_age_35_44_m: false,
      dash_age_35_44_f: false,
      dash_age_45_54_m: false,
      dash_age_45_54_f: false,
      dash_age_gre_54_m: false,
      dash_age_gre_54_f: false,
      dash_department_name: false,
      dash_department_count: false,
      dash_headcount: false,
      dash_todays_attendance: false,
      dash_position_name: false,
      dash_position_count: false,
      is_hr_manager: false,
      dash_holidays_filter_report_view_id: false,
      dash_holidays_filter_view_id: false,
      monthly_leaves_data: false,
      monthly_expenses_data: false,
      monthly_labels: false,
      showContactPopup: false,
      contactInfo: {
        phone: false,
        mobile: false,
        email: false,
        department: false,
        manager: false,
      },
    })

    onWillStart(async () => {
      await loadBundle("web.chartjs_lib")
      try {
        await Promise.all([
          loadJS("/hr_employee_dashboard/static/src/lib/jspdf.debug.js"),
          loadJS("/hr_employee_dashboard/static/src/lib/html2canvas.js"),
        ])
      } catch (error) {
        if (!(error instanceof AssetsLoadingError)) {
          throw error
        }
      }
      await this.fetch_data()
    })

    onMounted(async () => {
      await this.render_graphs()
    })
  }

  async fetch_data() {
    var result = await rpc("/hr_employee_dashboard/dashboard_employee_data", {
      user_id: user.userId || false,
    })

    if (result && result.length > 0) {
      const data = result[0]

      this.state.dash_employee_id = data.dash_employee_id
      this.state.dash_image = data.dash_image
      this.state.dash_job_name = data.dash_job_name
      this.state.dash_name = data.dash_name
      this.state.is_hr_manager = data.is_hr_manager
      // Manager-specific metrics
      this.state.manager_leaves_to_approve = data.manager_leaves_to_approve
      this.state.manager_expenses_to_approve = data.manager_expenses_to_approve
      this.state.manager_leaves_approved = data.manager_leaves_approved
      this.state.manager_expenses_approved = data.manager_expenses_approved
      this.state.manager_total_employees = data.manager_total_employees
      this.state.manager_employees_checked_in = data.manager_employees_checked_in
      this.state.manager_employees_absent = data.manager_employees_absent
      // Employee-specific metrics
      this.state.employee_own_leaves_to_approve = data.employee_own_leaves_to_approve
      this.state.employee_own_expenses_to_approve = data.employee_own_expenses_to_approve
      this.state.employee_own_leaves_approved = data.employee_own_leaves_approved
      this.state.employee_own_expenses_approved = data.employee_own_expenses_approved
      this.state.employee_own_attendance_status = data.employee_own_attendance_status
      this.state.employee_own_check_in_time = data.employee_own_check_in_time
      this.state.employee_own_check_out_time = data.employee_own_check_out_time
      this.state.dash_leaves_count = data.dash_leaves_count
      this.state.dash_male_count = data.dash_male_count
      this.state.dash_female_count = data.dash_female_count
      this.state.dash_top_nationalities_count = data.dash_top_nationalities_count
      this.state.dash_top_nationalities = data.dash_top_nationalities
      this.state.dash_leaves_to_approve = data.dash_leaves_to_approve
      this.state.dash_allowcations_to_approve = data.dash_allowcations_to_approve
      this.state.dash_expenses_to_approve = data.dash_expenses_to_approve
      this.state.dash_expenses_approved = data.dash_expenses_approved
      this.state.dash_age_les_24_m = data.dash_age_les_24_m
      this.state.dash_age_les_24_f = data.dash_age_les_24_f
      this.state.dash_age_25_34_m = data.dash_age_25_34_m
      this.state.dash_age_25_34_f = data.dash_age_25_34_f
      this.state.dash_age_35_44_m = data.dash_age_35_44_m
      this.state.dash_age_35_44_f = data.dash_age_35_44_f
      this.state.dash_age_45_54_m = data.dash_age_45_54_m
      this.state.dash_age_45_54_f = data.dash_age_45_54_f
      this.state.dash_department_name = data.dash_department_name
      this.state.dash_department_count = data.dash_department_count
      this.state.dash_headcount = data.dash_headcount
      this.state.dash_todays_attendance = data.dash_todays_attendance
      this.state.dash_position_name = data.dash_position_name
      this.state.dash_position_count = data.dash_position_count
      this.state.dash_holidays_filter_report_view_id = data.dash_holidays_filter_report_view_id
      this.state.dash_holidays_filter_view_id = data.dash_holidays_filter_view_id
      this.state.monthly_leaves_data = data.monthly_leaves_data
      this.state.monthly_expenses_data = data.monthly_expenses_data
      this.state.monthly_labels = data.monthly_labels
      this.state.dash_employee_phone = data.dash_employee_phone
      this.state.dash_employee_mobile = data.dash_employee_mobile
      this.state.dash_employee_email = data.dash_employee_email
      this.state.dash_employee_department_name = data.dash_employee_department_name
      this.state.dash_manager_name = data.dash_manager_name
    }
  }

  getbgcolor(length) {
    var colors = [
      "#3e95cd",
      "#8e5ea2",
      "#3cba9f",
      "#e8c3b9",
      "#c45850",
      "#FF6384",
      "#36A2EB",
      "#FFCE56",
      "#4BC0C0",
      "#9966FF",
    ]
    var color = []
    for (var i = 0; i < length; i++) {
      color.push(colors[i % colors.length])
    }
    return color
  }

  async render_graphs() {
    // Gender Details Chart
    await this.renderGenderChart()

    // Nationality Details Chart
    await this.renderNationalityChart()

    // Department Details Chart
    await this.renderDepartmentChart()

    // Attendance Details Chart
    await this.renderAttendanceChart()

    // Position Details Chart
    await this.renderPositionChart()

    // Monthly Stats Chart (for managers)
    if (this.state.is_hr_manager) {
      await this.renderMonthlyStatsChart()
    }
  }

  async renderGenderChart() {
    if (!this.genderChartRef.el) return

    var gender_chart_id = "chart_" + Math.random().toString(36).substr(2, 9)
    this.genderChartRef.el.innerHTML = ""

    var canvasGenderDetailsContainer = document.createElement("div")
    canvasGenderDetailsContainer.className = "o_graph_gender_details_container"
    canvasGenderDetailsContainer.style.height = "250px"

    this.canvasGenderDetails = document.createElement("canvas")
    this.canvasGenderDetails.height = 250
    this.canvasGenderDetails.id = gender_chart_id

    canvasGenderDetailsContainer.appendChild(this.canvasGenderDetails)
    this.genderChartRef.el.appendChild(canvasGenderDetailsContainer)

    var ctxGenderDetails = this.canvasGenderDetails
    this.GenderDetails = new Chart(ctxGenderDetails, {
      type: "pie",
      data: {
        labels: ["Male", "Female"],
        datasets: [
          {
            backgroundColor: ["#3e95cd", "#8e5ea2"],
            data: [this.state.dash_male_count, this.state.dash_female_count],
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
      },
    })
  }

  async renderNationalityChart() {
    if (!this.nationalityChartRef.el || !this.state.dash_top_nationalities) return

    var nationality_chart_id = "chart_" + Math.random().toString(36).substr(2, 9)
    this.nationalityChartRef.el.innerHTML = ""

    var canvasNationalityDetailsContainer = document.createElement("div")
    canvasNationalityDetailsContainer.className = "o_graph_nationality_details_container"
    canvasNationalityDetailsContainer.style.height = "280px"

    this.canvasNationalityDetails = document.createElement("canvas")
    this.canvasNationalityDetails.height = 280
    this.canvasNationalityDetails.id = nationality_chart_id

    canvasNationalityDetailsContainer.appendChild(this.canvasNationalityDetails)
    this.nationalityChartRef.el.appendChild(canvasNationalityDetailsContainer)

    var ctxNationalityDetails = this.canvasNationalityDetails
    this.NationalityDetails = new Chart(ctxNationalityDetails, {
      type: "bar",
      data: {
        labels: this.state.dash_top_nationalities,
        datasets: [
          {
            backgroundColor: this.getbgcolor(this.state.dash_top_nationalities.length),
            data: this.state.dash_top_nationalities_count,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
        indexAxis: "y",
        scales: {
          x: {
            beginAtZero: true,
          },
        },
      },
    })
  }

  async renderDepartmentChart() {
    if (!this.departmentChartRef.el || !this.state.dash_department_name || !this.state.dash_department_count) {
      return
    }

    // Validate data arrays
    if (!Array.isArray(this.state.dash_department_name) || !Array.isArray(this.state.dash_department_count)) {
      console.error("Department chart data is not in array format")
      return
    }

    if (this.state.dash_department_name.length !== this.state.dash_department_count.length) {
      console.error("Department chart data arrays have different lengths")
      return
    }

    if (this.state.dash_department_name.length === 0) {
      console.log("No department data available")
      // Show "No Data" message
      this.departmentChartRef.el.innerHTML =
        '<div style="text-align: center; padding: 50px; color: #7f8c8d;"><i class="fa fa-info-circle"></i><br>No Department Data Available</div>'
      return
    }

    var department_chart_id = "chart_" + Math.random().toString(36).substr(2, 9)
    this.departmentChartRef.el.innerHTML = ""

    var canvasDepartmentDetailsContainer = document.createElement("div")
    canvasDepartmentDetailsContainer.className = "o_graph_department_details_container"
    canvasDepartmentDetailsContainer.style.height = "280px"

    this.canvasDepartmentDetails = document.createElement("canvas")
    this.canvasDepartmentDetails.height = 280
    this.canvasDepartmentDetails.id = department_chart_id

    canvasDepartmentDetailsContainer.appendChild(this.canvasDepartmentDetails)
    this.departmentChartRef.el.appendChild(canvasDepartmentDetailsContainer)

    var ctxDepartmentDetails = this.canvasDepartmentDetails

    console.log("==this.state.dash_department_name", this.state.dash_department_name, this.state.dash_department_count)
    try {
      this.DepartmentDetails = new Chart(ctxDepartmentDetails, {
        type: "bar",
        data: {
          labels: this.state.dash_department_name,
          datasets: [
            {
              label: "Employees",
              backgroundColor: this.getbgcolor(this.state.dash_department_name.length),
              data: this.state.dash_department_count,
              borderWidth: 1,
              borderColor: "#ffffff",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              callbacks: {
                label: (context) => context.parsed.x + " employees",
              },
            },
          },
          indexAxis: "y",
          scales: {
            x: {
              beginAtZero: true,
              ticks: {
                stepSize: 1,
                callback: (value) => (Number.isInteger(value) ? value : ""),
              },
              grid: {
                color: "rgba(0, 0, 0, 0.1)",
              },
            },
            y: {
              grid: {
                display: false,
              },
              ticks: {
                maxTicksLimit: 10,
                font: {
                  size: 11,
                },
              },
            },
          },
          layout: {
            padding: {
              left: 10,
              right: 10,
              top: 10,
              bottom: 10,
            },
          },
        },
      })

      console.log("Department chart rendered successfully with data:", {
        labels: this.state.dash_department_name,
        data: this.state.dash_department_count,
      })
    } catch (error) {
      console.error("Error rendering department chart:", error)
      this.departmentChartRef.el.innerHTML =
        '<div style="text-align: center; padding: 50px; color: #e74c3c;"><i class="fa fa-exclamation-triangle"></i><br>Error loading chart</div>'
    }
  }

  async renderAttendanceChart() {
    if (!this.attendanceChartRef.el) return

    var attendance_chart_id = "chart_" + Math.random().toString(36).substr(2, 9)
    this.attendanceChartRef.el.innerHTML = ""

    var canvasAttendanceDetailsContainer = document.createElement("div")
    canvasAttendanceDetailsContainer.className = "o_graph_attendance_details_container"
    canvasAttendanceDetailsContainer.style.height = "280px"

    this.canvasAttendanceDetails = document.createElement("canvas")
    this.canvasAttendanceDetails.height = 280
    this.canvasAttendanceDetails.id = attendance_chart_id

    canvasAttendanceDetailsContainer.appendChild(this.canvasAttendanceDetails)
    this.attendanceChartRef.el.appendChild(canvasAttendanceDetailsContainer)

    var ctxAttendanceDetails = this.canvasAttendanceDetails
    this.AttendanceDetails = new Chart(ctxAttendanceDetails, {
      type: "pie",
      data: {
        labels: ["Present", "Total Headcount"],
        datasets: [
          {
            backgroundColor: ["#3cba9f", "#e8c3b9"],
            data: [this.state.dash_todays_attendance, this.state.dash_headcount],
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
      },
    })
  }

  async renderPositionChart() {
    if (!this.positionChartRef.el || !this.state.dash_position_name) return

    var position_chart_id = "chart_" + Math.random().toString(36).substr(2, 9)
    this.positionChartRef.el.innerHTML = ""

    var canvasPositionDetailsContainer = document.createElement("div")
    canvasPositionDetailsContainer.className = "o_graph_position_details_container"
    canvasPositionDetailsContainer.style.height = "280px"

    this.canvasPositionDetails = document.createElement("canvas")
    this.canvasPositionDetails.height = 280
    this.canvasPositionDetails.id = position_chart_id

    canvasPositionDetailsContainer.appendChild(this.canvasPositionDetails)
    this.positionChartRef.el.appendChild(canvasPositionDetailsContainer)

    var ctxPositionDetails = this.canvasPositionDetails
    this.PositionDetails = new Chart(ctxPositionDetails, {
      type: "doughnut",
      data: {
        labels: this.state.dash_position_name,
        datasets: [
          {
            backgroundColor: this.getbgcolor(this.state.dash_position_name.length),
            data: this.state.dash_position_count,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
        },
      },
    })
  }

  async renderMonthlyStatsChart() {
    if (!this.monthlyStatsChartRef.el || !this.state.monthly_labels) return

    var monthly_chart_id = "chart_" + Math.random().toString(36).substr(2, 9)
    this.monthlyStatsChartRef.el.innerHTML = ""

    var canvasMonthlyStatsContainer = document.createElement("div")
    canvasMonthlyStatsContainer.className = "o_graph_monthly_stats_container"
    canvasMonthlyStatsContainer.style.height = "400px"
    canvasMonthlyStatsContainer.style.width = "100%"

    this.canvasMonthlyStats = document.createElement("canvas")
    this.canvasMonthlyStats.height = 400
    this.canvasMonthlyStats.style.width = "100%"
    this.canvasMonthlyStats.id = monthly_chart_id

    canvasMonthlyStatsContainer.appendChild(this.canvasMonthlyStats)
    this.monthlyStatsChartRef.el.appendChild(canvasMonthlyStatsContainer)

    var ctxMonthlyStats = this.canvasMonthlyStats
    this.MonthlyStats = new Chart(ctxMonthlyStats, {
      type: "line",
      data: {
        labels: this.state.monthly_labels,
        datasets: [
          {
            label: "Leaves Approved",
            data: this.state.monthly_leaves_data,
            borderColor: "#3e95cd",
            backgroundColor: "rgba(62, 149, 205, 0.1)",
            tension: 0.4,
            fill: true,
          },
          {
            label: "Expenses Approved",
            data: this.state.monthly_expenses_data,
            borderColor: "#8e5ea2",
            backgroundColor: "rgba(142, 94, 162, 0.1)",
            tension: 0.4,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: {
              usePointStyle: true,
              padding: 20,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(0, 0, 0, 0.1)",
            },
            ticks: {
              stepSize: 1,
            },
          },
          x: {
            grid: {
              color: "rgba(0, 0, 0, 0.1)",
            },
          },
        },
        elements: {
          point: {
            radius: 6,
            hoverRadius: 8,
          },
          line: {
            borderWidth: 3,
          },
        },
      },
    })
  }

  onPrint() {
    const dashboardContainer = document.querySelector("#dashboard_container")
    if (!dashboardContainer) {
      console.error("Dashboard container not found.")
      return
    }

    html2canvas(dashboardContainer)
      .then((canvas) => {
        try {
          const dataURL = canvas.toDataURL("image/jpeg")
          const pdf = new jsPDF("landscape")
          pdf.addImage(dataURL, "JPEG", 5, 10, 287, 200)
          pdf.save("HR_Dashboard.pdf")
        } catch (error) {
          console.error("Error generating PDF:", error)
        }
      })
      .catch((error) => {
        console.error("Error capturing the dashboard:", error)
      })
  }

  async refreshData() {
    await this.fetch_data()
    await this.render_graphs()
  }

  openLeaves() {
    this.env.services.action.doAction("hr_holidays.hr_leave_action_my")
  }

  // Navigation methods
  openLeavesToApprove() {
    this.env.services.action.doAction("hr_holidays.hr_leave_action_action_approve_department")
  }

  openAllocationsToApprove() {
    this.env.services.action.doAction("hr_holidays.hr_leave_allocation_action_approve")
  }


  openValidatedLeavesThisMonth() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.leave",
        name: "Leaves Approved (This Month)",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [
            ["state", "=", "validate"],
            ["create_date", ">=", firstDayOfMonth.toISOString().slice(0, 10)],
        ],
    });
  }

  openApprovedExpenses() {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.expense.sheet",
        name: "Expenses Approved (This Month)",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [
            ["state", "=", "approve"],
            ["create_date", ">=", firstDayOfMonth.toISOString().slice(0, 10)],
        ],
    });
  }

  openExpensesToApprove() {
    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.expense.sheet",
        name: "Expenses to Approve",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [["state", "=", "submit"]],
    });
  }

  openMyLeavesPending() {
    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.leave",
        name: "My Leaves Pending",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [
            ["state", "=", "confirm"],
        ],
    });
  }

  openMyExpensesPending(){
    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.expense.sheet",
        name: "My Expenses Pending",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [["state", "=", "submit"]],
    });
  }

  openMyLeavesApproved(){
    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.leave",
        name: "My Leaves Approved",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [
            ["state", "=", "validate"],
        ],
    });
  }

  openMyExpensesApproved(){
    this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: "hr.expense.sheet",
        name: "My Expenses Approved",
        view_mode: "tree,form",
        views: [[false, "list"], [false, "form"]],
        domain: [["state", "=", "done"]],
    });
  }

  showContactPopup(event) {
    // Get contact type from data attribute if needed
    const contactType = event.target.getAttribute("data-contact-type")

    // Set contact information (you can customize this based on your data)
    this.state.contactInfo = {
      phone: this.state.dash_employee_phone || "+1 (555) 123-4567",
      mobile: this.state.dash_employee_mobile || "+1 (555) 987-6543",
      email:
        this.state.dash_employee_email || this.state.dash_name
          ? this.state.dash_name.toLowerCase().replace(" ", ".") + "@company.com"
          : "employee@company.com",
      department: this.state.dash_employee_department_name || "Human Resources",
      manager: this.state.dash_manager_name || "John Manager",
    }

    this.state.showContactPopup = true
  }

  hideContactPopup() {
    this.state.showContactPopup = false
  }

  callNumber(phoneNumber) {
    if (phoneNumber) {
      // Remove any non-numeric characters except + and spaces
      const cleanNumber = phoneNumber.replace(/[^\d+\s-()]/g, "")
      window.open(`tel:${cleanNumber}`, "_self")
    }
  }

  sendEmail(emailAddress) {
    if (emailAddress) {
      const subject = encodeURIComponent("Contact from HR Dashboard")
      const body = encodeURIComponent("Hello,\n\nI am contacting you from the HR Dashboard.\n\nBest regards")
      window.open(`mailto:${emailAddress}?subject=${subject}&body=${body}`, "_self")
    }
  }
}

registry.category("actions").add("hr_employee_dashboard.dashboard", HRDashboard)