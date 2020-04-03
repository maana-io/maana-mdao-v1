
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

## multiDisciplineProblem

query{
  multiDisciplineProblem(
    

    
  	independantVariables:[
      {
        id: "x"
        value: 1.0
      },
      {
        id: "z1"
        value: 5.0
      },
      {
        id: "z2"
        value: 2.0
      }

    ]
    group: {
      id: "group"
      name: "cycle"
      explicitDisciplines:[
        	{
            id: "d1"
            component:{
              id: "d1"
              name: "d1"
              equation: "y1 = z1**2 + z2 + x - 0.2*y2"
              
            }
            promotesInputs: ["x", "z2", "y2"]
            promotesOutputs: ["y1"]
          }
        {
            id: "d2"
            component:{
              id: "d2"
              name: "d2"
              equation: "y2 = y1**.5 + z1 + z2"
              
            }
            promotesInputs: ["y1", "z1", "z2"]
            promotesOutputs: ["y2"]
          }
      ]
      
    }
    
    constraints:[
      {
        id: "const.con1"
        name: "con1"
        lowerBound: 0
        upperBound: 10
        equation: "con1 = 3.16 - y1"
        promotes: ["con1", "y1"]
      }
       {
        id: "const.con2"
        name: "con2"
        lowerBound: 0
        upperBound: 10
        equation: "con2 = y2 - 24.0"
        promotes: ["con2", "y2"]
      }
    ]
    objective:{
      id: "obj"
      equation: "obj = x**2 + z2 + y1 + exp(-y2)"
      promotes:["x", "z2", "y1", "y2", "obj"]
    }
  
  ){
    id
    value
  }
}