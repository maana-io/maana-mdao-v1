# imports

#import openMDAO libary
import openmdao.api as om
import numpy as np

# mappings

def resolver_multi_disicipline_problem_mapper(query):
    query.set_field("multiDisciplineProblem", resolve_multi_discipline_problem)

def resolver_problem_mapper(query):
    query.set_field("problem",resolve_problem)

    
# resolvers

def resolve_multi_discipline_problem(*_,  driver, independantVariables, designVariables, group, constraints, objective):
    
    # build the problem
    prob = om.Problem()
    
    ####    SETUP THE MODEL     ####
    # add group to hold disciplines
    cycle = prob.model.add_subsystem(group['name'], om.Group(), promotes=['*'])

    # create the independant variables with default values
    indeps = prob.model.add_subsystem('indeps', om.IndepVarComp(), promotes=['*'])
    # provides default values for independant variables
    for indep in independantVariables:
        indeps.add_output(indep['id'], indep['value'])


    #cycle.add_subsystem('d1', d1(), promotes_inputs=['x', 'z', 'y2'],
    #                        promotes_outputs=['y1'])
    #cycle.add_subsystem('d2', d2(), promotes_inputs=['z', 'y1'],
    #                       promotes_outputs=['y2'])

    for d in group['explicitDisciplines']:
        cycle.add_subsystem(d['component']['name'],  om.ExecComp(d['component']["equation"]),  promotes_inputs=d['promotesInputs'],
                            promotes_outputs=d['promotesOutputs'])
    

    # NEED TO ADD A WAY TO CHOOSE THE SOLVER FOR THE GROUP
    # Nonlinear Block Gauss Seidel is a gradient free solver
    cycle.nonlinear_solver = om.NonlinearBlockGS()

    ### SETUP OBJECTIVE
    #'obj = x**2 + z1 + y1 + exp(-y2)'
    #z=np.array([0.0, 0.0]), x=0.0),
    prob.model.add_subsystem(objective['id'], om.ExecComp(objective['equation']), promotes=objective['promotes'])


    ### SETUP CONSTRAINTS
    for c in constraints:
        prob.model.add_subsystem(c['name'], om.ExecComp(c['equation']), promotes=c['promotes'])
    

    #prob.model = SellarMDA()

    ## OPTIMIZIZE THE MODEL
    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options['optimizer'] = driver['optimizer']
    prob.driver.options['tol'] = 1e-8  
    prob.driver.options['maxiter'] = 100  

    # add design variables
    for designVar in designVariables:
        prob.model.add_design_var(designVar['id'], lower=designVar['lowerBound'], upper=designVar['upperBound'])


    prob.model.add_objective('obj')

    # add the contraints
    for const in constraints:
        prob.model.add_constraint(const['name'], const['upperBound'])


    prob.setup()

    # since all variables are promoted to the top of the model we can set
    # them here.


    # SET INITIAL VALUES
    #prob['z1'] = -1.
    #prob['z2'] = -1.
    #prob['x'] = 2.

    ## ADD AN OPTION TO RUN THE MODEL ONLY
    #

    results = []
    if(driver["optimize"] == True):
        prob.set_solver_print(level=0)
        prob.model.approx_totals()
        prob.run_driver()
        results.append({'id': objective['id'], 'value': prob[objective['id']][0]})
        for d in designVariables:
            results.append({'id': d['id'], 'value': prob[d['id']][0]})
        return results
    elif(driver["optimize"] == False):
        # running model only
        # set any intial values on the model
        for i in independantVariables:
            prob[i['id']] = i['value']
        prob.run_model()
        results.append({'id': objective['id'], 'value': prob[objective['id']][0]})
        for ec in group['explicitDisciplines']:
            for o in ec['promotesOutputs']:
                results.append({'id': o, 'value': prob[o][0]})
        for c in constraints:
            results.append({'id': c['name'], 'value': prob[c['name']][0]})
        return results

def resolve_problem(*_, driver, independantVariables, designVariables, explicitComponent, constraints, objective):

    # build the problem
    prob = om.Problem()

    # create the independant variables

    indeps = prob.model.add_subsystem('indeps', om.IndepVarComp())

    # provides initial values for independant variables
    for indep in independantVariables:
        indeps.add_output(indep['id'], indep['value'])
    
    # add the "Explicit Component" in this case a "paraloboid"
    #prob.model.add_subsystem('parab', Paraboloid())
    # 'f = (x-3)**2 + x*y + (y+4)**2 - 3'

    prob.model.add_subsystem(explicitComponent['name'], om.ExecComp(explicitComponent["equation"])) 

    for const in constraints:
        prob.model.add_subsystem(const['name'], om.ExecComp(const['equation']))
        prob.model.add_constraint(const['id'], lower=const['lowerBound'], upper=const['upperBound']) 

    for indep in independantVariables:
        prob.model.connect('indeps.' + indep['id'], [explicitComponent['name'] + '.' + indep['id'], constraints[0]['name'] + '.' + indep['id'] ])

    # add design variables
    for designVar in designVariables:
        prob.model.add_design_var(designVar['id'], lower=designVar['lowerBound'], upper=designVar['upperBound'])
    
    # add objective
    prob.model.add_objective(objective['id'])

    # create the driver
    prob.driver = om.ScipyOptimizeDriver()
    prob.driver.options['optimizer'] = driver['optimizer']
      
    prob.setup()
    prob.run_driver()

    results = [
        {
            'id': objective['id'],
            'value': prob[objective['id']]
        }
    ]

    for designVar in designVariables:
        results.append({'id': designVar['id'], 'value': prob[designVar['id']]})

    return results