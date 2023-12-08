<script>
    function calculateLoan() {
      const loanAmount = parseFloat(document.getElementById('loan-amount').value);
      const interestRate = parseFloat(document.getElementById('interest-rate').value) / 100;
      const loanDuration = parseInt(document.getElementById('loan-duration').value);
      const startDate = document.getElementById('start-date').value;

      const { monthlyEMI, totalInterest, totalAmount, repaymentSchedule } = calculateLoanDetails(loanAmount, interestRate, loanDuration, startDate);

      document.getElementById('loan-amount-result').textContent = `${loanAmount.toFixed(2)}`;
      document.getElementById('monthly-emi').textContent = `${monthlyEMI.toFixed(2)}`;
      document.getElementById('total-interest').textContent = `${totalInterest.toFixed(2)}`;
      document.getElementById('total-amount').textContent = `${totalAmount.toFixed(2)}`;

      generateRepaymentSchedule(repaymentSchedule);
      generatePieChart(loanAmount, totalInterest);
    }

    function calculateLoanDetails(loanAmount, interestRate, loanDuration, startDate) {
      const monthlyInterest = interestRate / 12;
      const numerator = loanAmount * monthlyInterest * Math.pow(1 + monthlyInterest, loanDuration);
      const denominator = Math.pow(1 + monthlyInterest, loanDuration) - 1;
      const monthlyEMI = numerator / denominator;

      const repaymentSchedule = generateRepaymentScheduleArray(loanAmount, monthlyEMI, loanDuration, startDate, interestRate);

      const totalInterest = monthlyEMI * loanDuration - loanAmount;
      const totalAmount = totalInterest + loanAmount;

      return { monthlyEMI, totalInterest, totalAmount, repaymentSchedule };
    }

    function generateRepaymentScheduleArray(loanAmount, monthlyEMI, loanDuration, startDate, interestRate) {
      const scheduleArray = [];
      let balance = loanAmount;

      for (let i = 0; i < loanDuration; i++) {
        const date = new Date(startDate);
        date.setMonth(date.getMonth() + i);

        const interest = balance * (interestRate / 12);
        const principal = monthlyEMI - interest;
        balance -= principal;

        scheduleArray.push({
          date: date.toISOString().split('T')[0],
          principalAmount: principal.toFixed(2),
          interest: interest.toFixed(2),
          balance: balance.toFixed(2),
        });
      }

      return scheduleArray;
    }

    function generateRepaymentSchedule(repaymentSchedule) {
      const scheduleContainer = document.getElementById('repayment-schedule').querySelector('table');

      scheduleContainer.innerHTML = '<tr><th>Date</th><th>Principal Amount</th><th>Interest</th><th>Balance</th></tr>';

      for (const entry of repaymentSchedule) {
        scheduleContainer.innerHTML += `<tr><td>${entry.date}</td><td>${entry.principalAmount}</td><td>${entry.interest}</td><td>${entry.balance}</td></tr>`;
      }
    }

    function generatePieChart(loanAmount, totalInterest) {
      const ctx = document.getElementById('pie-chart').getContext('2d');

      const data = {
        labels: ['Loan Amount', 'Total Interest'],
        datasets: [{
          data: [loanAmount, totalInterest],
          backgroundColor: ['#4caf50', '#f44336'],
        }],
      };

      const options = {
        responsive: true,
        maintainAspectRatio: false,
      };

      new Chart(ctx, {
        type: 'pie',
        data: data,
        options: options,
      });
    }
  </script>
