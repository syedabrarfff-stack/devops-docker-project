(function(){
  var calls = document.getElementById('calls');
  var miss = document.getElementById('miss');
  var conv = document.getElementById('conv');
  var callsVal = document.getElementById('callsVal');
  var missVal = document.getElementById('missVal');
  var convVal = document.getElementById('convVal');
  var resultAmt = document.getElementById('resultAmt');

  function fmt(n){ return '$' + Math.round(n).toLocaleString('en-US'); }

  function update(){
    var c = parseInt(calls.value, 10);
    var m = parseInt(miss.value, 10);
    var missedCalls = Math.round(c * (m/100));
    var maxConv = Math.max(1, missedCalls);
    if (parseInt(conv.value,10) > maxConv) { conv.value = maxConv; }
    var recovered = parseInt(conv.value, 10);

    callsVal.textContent = c;
    missVal.textContent = m + '%';
    convVal.textContent = recovered + ' of ' + missedCalls + ' missed';

    var low = recovered * 600;
    var high = recovered * 1200;
    resultAmt.textContent = fmt(low) + ' – ' + fmt(high);
  }

  [calls, miss, conv].forEach(function(el){ el.addEventListener('input', update); });
  update();

  if ('IntersectionObserver' in window) {
    document.documentElement.classList.add('js-anim');
    var obs = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target); } });
    }, { threshold: 0.12 });
    document.querySelectorAll('.reveal').forEach(function(el){ obs.observe(el); });
  }
})();
