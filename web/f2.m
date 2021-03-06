% LAGOON MODEL:  FOUR COUPLED DIFFERENTIAL EQUATIONS:
%
% UNINFECTED  -> ADSORBED  -> PRODUCTIVE  ->  PHAGE
%  (cells)        (cells)      (cells)      (particles)
%
% The x[1,2,3,4] equations represent total number of cells, phage, etc.
% The differential (change in population) has units of cells/minute
%
function xdot = f2(x,t)
  global kg ad ec pp fr h0 vol;
% These variables are read in from the ES_params.txt file
% which is created through user interaction with the web page

  pm = 1;  % How much to make the g-model different from f (upper/lower bounds for simulation)
  % Maybe this should a be noise source instead of a fixed offset?
  lkg = delta(kg, 0.02*pm); % Local (varied) normal E. coli doubling time in minutes
  lad = delta(ad, 0.1*pm);  % Local (varied) adsorption coefficient mL/min
  lec = delta(ec, 0.1*pm);  % Local (varied) eclipse interval  (6 min?)
  lpp = delta(pp, 0.05*pm);  % Local (varied) phage production per cell-hour

% Inhibited growth rates (longer doubling times) for subsequent stages of E. coli
% Ultimately this should be measured for given strains of E. coli and M13
  inhibit = 1.1;
% Infected cells have inhibited growth rate relative to healthy host cells
  kgp = lkg*inhibit;
% Productive cells have inhibited growth rate relative to merely infected cells
  kgpp = kgp*inhibit;

% INFLOW = Flow rate in volumes/hour * concentration cells/ML * volume mL = number of cells
% Growth = Number of Cells * Growth constant [ ln(2) / doubling-time ]    = number of cells
%
% Infection = (Total Number of Cells * Total Number of Phage * Adsorption Constant)/total Volume = Fraction Infected
% (Adsorption factor units are vol/time)
%
% fr is flow rate in volumes per hour:  fr(vol/hour)*vol(mL/vol)/60(min/hour) is flow rate in mL/min   
% h0 is input concentration in cells/mL:   h0(cells/mL)  *  fr*vol/60(mL/min) is cells/min
%    
% Adsorption constant is in mL/min (physical interpretation: Brownian motion. Think of mL as cubic-centimeter)
% lad*x(1)*x(4)     (mL/min)*(cells)*(total phage)  (interaction-volume/min)*(targets)*(missiles)
%
% Note uninfected host can become quite scarce, while phage is become numerous,
% reducing the chance that a given phage will find a target.
% A crutial point for emerging populations.
% The total number of host cells (collision opportunities for phage) is x1+x2*x3
% while only x1 collisions can result in an infection, so probability of collision is: x1/(x1+x2+x3)
%
% (1) Uninfected Host flowing in at Dilution Constant * Cells/mL
%           + INFLOW      +    GROWTH         - OUTFLOW    - TRANSFORMATION
%
% This (commented out) tries to account for low probability of phage <-> uninfected host collisions
%  xdot(1) =   h0*fr*vol/60  + (log(2)/lkg)*x(1) - fr*x(1)/60 - (lad/vol)*x(4)*(x(1)/(x(1)+x(2)+x(3)))

  xdot(1) =   h0*fr*vol/60  + (log(2)/lkg)*x(1) - fr*x(1)/60 - (lad/vol)*x(4)*x(1);

% (2) Infected Host (previous TRANSFORMED is this equation's INFLOW)
%          (mL/min) * phage/vol * (cells/vol)/(cells/vol)

% Experimental (as above) for lower probability phage <-> uninfected host collisions
%  xdot(2) =  (lad/vol)*x(4)*(x(1)/(x(1)+x(2)+x(3))) + (log(2)/kgp)*x(2) - fr*x(2)/60  -  x(2)/lec;

% Transformation term represents   1/(eclipse interval) cells coming out of eclipse (per minute)
% NB: Infected cells come out of eclipse together after 6 minutes,
% Not 1/6 of them per minute (as in this equation).  Exactly the same only in steady state.

   xdot(2) =  (lad/vol)*x(4)*x(1) + (log(2)/kgp)*x(2) - fr*x(2)/60  -  x(2)/lec;

% (3) Productive Host: INFLOW is cells leaving eclipse, plus growth, minus dilution

  xdot(3) =  x(2)/lec   + (log(2)/kgpp)*x(3)  - fr*x(3)/60;  % No transformation output
  
% (4) Phage  + Production + No Growth Term - OUTFLOW  - No Transformation Term

  xdot(4) =  lpp*x(3)/60                - fr*x(4)/60;
  
endfunction

