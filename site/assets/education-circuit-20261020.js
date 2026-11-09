/* ResoArc Education: simplified series LED circuit. No data is sent out. */
(()=>{'use strict';
 const $=id=>document.getElementById(id);
 const controls=['volts','res','connected','resistor','polarity'];
 const values=controls.map($);
 if(values.some(v=>!v)) return;
 function compute(){
  const volts=Number($('volts').value),r=Number($('res').value);
  const sw=$('connected').checked,withResistor=$('resistor').checked,polarity=$('polarity').checked;
  $('voltsValue').textContent=volts+' V';
  $('resValue').textContent=r+' Ω';
  const effectiveR=withResistor?r:0;
  const connected=sw&&polarity;
  const voltageAvailable=volts>2;
  const calculable=connected&&voltageAvailable&&effectiveR>0;
  const current=calculable?1000*(volts-2)/effectiveR:0;
  const bright=calculable?Math.min(1,current/20):0;
  $('circuitGlow').setAttribute('opacity',String(bright*.86));
  $('circuitCurrent').textContent=(calculable?current.toFixed(1)+' mA':(connected&&voltageAvailable?'計算不可':'0.0 mA'));
  $('circuitCurrentLabel').textContent=calculable?current.toFixed(1)+' mA':'0.0 mA';
  $('circuitSwitch').setAttribute('d',sw?'M450 69L490 69':'M450 69L486 42');
  const status=$('circuitStatus'),hint=$('circuitHint'),led=$('circuitLedState');
  if(!sw){status.textContent='スイッチが開いているので電流は流れません。';led.textContent='消灯';hint.textContent='スイッチをONにするとどうなるか試そう。'}
  else if(!polarity){status.textContent='LEDの向きが反対なので点灯しません。';led.textContent='消灯';hint.textContent='LEDを正しい向きに戻してみよう。'}
  else if(!voltageAvailable){status.textContent='電圧が不足しているため、LEDは光りません。';led.textContent='消灯';hint.textContent='電池の電圧を2 Vより大きくしてみよう。'}
  else if(!withResistor||r===0){status.textContent='抵抗がありません。このモデルでは電流を安全に計算できません。';led.textContent='危険な条件';hint.textContent='実際の回路では過電流でLEDが壊れるおそれがあります。抵抗を入れましょう。'}
  else if(current>20){status.textContent='電流の目安を超えています（20mA超）。';led.textContent='過電流のおそれ';hint.textContent='抵抗値を大きくして、流れる電流を減らしてみよう。'}
  else{status.textContent='電気が流れています！';led.textContent=current<1?'ごく弱く点灯':current<8?'やや暗く点灯':'点灯';hint.textContent='抵抗を大きくしたときの電流を比べてみよう。'}
  $('circuitResistor').setAttribute('opacity',withResistor?'1':'.2');
  $('circuitLed').setAttribute('opacity',polarity?'1':'.65');
 }
 for(const x of values){x.addEventListener('input',compute);x.addEventListener('change',compute);}
 const preset={
 safe:{volts:5,res:330,connected:true,resistor:true,polarity:true},
 dim:{volts:5,res:1500,connected:true,resistor:true,polarity:true},
 off:{volts:5,res:330,connected:false,resistor:true,polarity:true},
 reverse:{volts:5,res:330,connected:true,resistor:true,polarity:false},
 };
 for(const button of document.querySelectorAll('[data-preset]')){
  button.addEventListener('click',()=>{
   const v=preset[button.dataset.preset];if(!v)return;
   for(const id of controls)$(id)[$(id).type==='checkbox'?'checked':'value']=v[id];
   compute();
  });
 }
 compute();
})();