
## Features

## Problem

http://openmdao.org/twodocs/versions/latest/basic_guide/first_optimization.html

# optimizer options

{'BFGS', 'shgo', 'dual_annealing', 'Newton-CG', 'TNC', 'differential_evolution', 'basinhopping', 'Nelder-Mead', 'trust-constr', 'CG', 'Powell', 'COBYLA', 'SLSQP', 'L-BFGS-B'}.",

## Queries

The following queries can be run from the graphQL playground

query{
  problem(
    
    driver: {
      id: "sciPy",
      optimizer: "COBYLA"
    }
  	independantVariables:[
      {
        id: "x"
        value: 3.0
      },
      {
        id: "y"
        value: -4.0
      }
    ]
    designVariables:[
      {
        id: "indeps.x"
        lowerBound: -50
        upperBound: 50
      }
      {
        id: "indeps.y"
        lowerBound: -50
        upperBound: 50
      }
    ]
    explicitComponent:{
      id:"paraboloid.f"
      name:"paraboloid"
      equation: "f = (x-3)**2 + x*y + (y+4)**2 - 3"
    }
    constraints:[
      {
        id: "const.g"
        name: "const"
        lowerBound: 0
        upperBound: 10
        equation: "g = x + y"
      }
    ]
    objective:{
      id: "paraboloid.f"
    }
  
  ){
    id
    value
  }
}