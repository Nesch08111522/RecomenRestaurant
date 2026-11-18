/* Rules are explicit and independent of DOM/event coordination. */
(() => {
  'use strict';
  window.ForestRules = Object.freeze({
    openingState(restaurant, now = new Date()) {
      const valid = /^([01]\d|2[0-3]):[0-5]\d$/;
      const start = restaurant.open_time, end = restaurant.close_time;
      if (!valid.test(start || '') || !valid.test(end || '')) return null;
      const time = new Intl.DateTimeFormat('en-GB', {timeZone:'America/Lima', hour:'2-digit', minute:'2-digit', hourCycle:'h23'}).format(now);
      const open = start <= end ? time >= start && time <= end : time >= start || time <= end;
      return open ? {label:'Abierto', className:'is-open'} : {label:'Cerrado', className:'is-closed'};
    }
  });
})();
