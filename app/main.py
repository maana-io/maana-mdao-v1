from ariadne import ObjectType, QueryType, MutationType, gql, make_executable_schema
from ariadne.asgi import GraphQL
from asgi_lifespan import Lifespan, LifespanMiddleware
from graphqlclient import GraphQLClient

# HTTP request library for access token call
import requests
# .env
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

#import openMDAO libary
import openmdao.api as om
import numpy as np

#import the schema
from app.types.types import mdao_types

def getAuthToken():
    authProvider = os.getenv('AUTH_PROVIDER')
    authDomain = os.getenv('AUTH_DOMAIN')
    authClientId = os.getenv('AUTH_CLIENT_ID')
    authSecret = os.getenv('AUTH_SECRET')
    authIdentifier = os.getenv('AUTH_IDENTIFIER')

    # Short-circuit for 'no-auth' scenario.
    if(authProvider == ''):
        print('Auth provider not set. Aborting token request...')
        return None

    url = ''
    if authProvider == 'keycloak':
        url = f'{authDomain}/auth/realms/{authIdentifier}/protocol/openid-connect/token'
    else:
        url = f'https://{authDomain}/oauth/token'

    payload = {
        'grant_type': 'client_credentials',
        'client_id': authClientId,
        'client_secret': authSecret,
        'audience': authIdentifier
    }

    headers = {'content-type': 'application/x-www-form-urlencoded'}

    r = requests.post(url, data=payload, headers=headers)
    response_data = r.json()
    print("Finished auth token request...")
    return response_data['access_token']


def getClient():

    graphqlClient = None

    # Build as closure to keep scope clean.

    def buildClient(client=graphqlClient):
        # Cached in regular use cases.
        if (client is None):
            print('Building graphql client...')
            token = getAuthToken()
            if (token is None):
                # Short-circuit for 'no-auth' scenario.
                print('Failed to get access token. Abandoning client setup...')
                return None
            url = os.getenv('MAANA_ENDPOINT_URL')
            client = GraphQLClient(url)
            client.inject_token('Bearer '+token)
        return client
    return buildClient()


# Define types using Schema Definition Language (https://graphql.org/learn/schema/)
# Wrapping string in gql function provides validation and better error traceback
type_defs = gql(mdao_types)
# Map resolver functions to Query fields using QueryType
query = QueryType()

# Resolvers are simple python functions

###

# test classes NOT USED BUT ARE FOR EXAMPLE
class d1(om.ExplicitComponent):
    """
    Component containing Discipline 1 -- no derivatives version.
    """

    def setup(self):

        # Global Design Variable
        self.add_input('z', val=np.zeros(2))

        # Local Design Variable
        self.add_input('x', val=0.)

        # Coupling parameter
        self.add_input('y2', val=1.0)

        # Coupling output
        self.add_output('y1', val=1.0)

        # Finite difference all partials.
        self.declare_partials('*', '*', method='fd')

    def compute(self, inputs, outputs):
        """
        Evaluates the equation
        y1 = z1**2 + z2 + x1 - 0.2*y2
        """
        z1 = inputs['z'][0]
        z2 = inputs['z'][1]
        x1 = inputs['x']
        y2 = inputs['y2']

        outputs['y1'] = z1**2 + z2 + x1 - 0.2*y2

class d2(om.ExplicitComponent):
    """
    Component containing Discipline 2 -- no derivatives version.
    """

    def setup(self):
        # Global Design Variable
        self.add_input('z', val=np.zeros(2))

        # Coupling parameter
        self.add_input('y1', val=1.0)

        # Coupling output
        self.add_output('y2', val=1.0)

        # Finite difference all partials.
        self.declare_partials('*', '*', method='fd')

    def compute(self, inputs, outputs):
        """
        Evaluates the equation
        y2 = y1**(.5) + z1 + z2
        """

        z1 = inputs['z'][0]
        z2 = inputs['z'][1]
        y1 = inputs['y1']

        # Note: this may cause some issues. However, y1 is constrained to be
        # above 3.16, so lets just let it converge, and the optimizer will
        # throw it out
        if y1.real < 0.0:
            y1 *= -1

        outputs['y2'] = y1**.5 + z1 + z2

class SellarMDA(om.Group):
    """
    Group containing the Sellar MDA.
    """

    def setup(self):
        indeps = self.add_subsystem('indeps', om.IndepVarComp(), promotes=['*'])
        indeps.add_output('x', 1.0)
        indeps.add_output('z', np.array([5.0, 2.0]))

        cycle = self.add_subsystem('cycle', om.Group(), promotes=['*'])
        cycle.add_subsystem('d1', d1(), promotes_inputs=['x', 'z', 'y2'],
                            promotes_outputs=['y1'])
        cycle.add_subsystem('d2', d2(), promotes_inputs=['z', 'y1'],
                            promotes_outputs=['y2'])

        # Nonlinear Block Gauss Seidel is a gradient free solver
        cycle.nonlinear_solver =om. NonlinearBlockGS()

        self.add_subsystem('obj_cmp', om.ExecComp('obj = x**2 + z[1] + y1 + exp(-y2)',
                                                  z=np.array([0.0, 0.0]), x=0.0),
                           promotes=['x', 'z', 'y1', 'y2', 'obj'])

        self.add_subsystem('con_cmp1', om.ExecComp('con1 = 3.16 - y1'),
                           promotes=['con1', 'y1'])
        self.add_subsystem('con_cmp2', om.ExecComp('con2 = y2 - 24.0'),
                           promotes=['con2', 'y2'])

@query.field("multiDisciplineProblem")
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
    #prob.run_model()



    prob.set_solver_print(level=0)

    prob.model.approx_totals()

    prob.run_driver()
    
    

    # EXAMPLE MODEL OUTPUT
    #prob['y1'][0], prob['y2'][0], prob['obj'][0], prob['con1'][0], prob['con2'][0])
    
    results = []

    #get objective value
    results.append({'id': objective['id'], 'value': prob[objective['id']][0]})

    # gets the output values
    #for ec in group['explicitDisciplines']:
    #    for o in ec['promotesOutputs']:
    #        results.append({'id': o, 'value': prob[o][0]})


    for d in designVariables:
        results.append({'id': d['id'], 'value': prob[d['id']][0]})
    #for c in constraints:
    #    results.append({'id': c['name'], 'value': prob[c['name']][0]})

    return results



#problem(driver: DriverAsInput!, independantVariables: [IndependantVariableComponentAsInput!]!, designVariables: [DesignVariableAsInput!]!, explicitComponent: ExplicitComponentAsInput!, constraints: [ConstraintAsInput!]!, objective: ObjectiveAsInput!): [Result]
@query.field("problem")
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


# --- ASGI app

# Create executable GraphQL schema
schema = make_executable_schema(type_defs, [query])

# --- ASGI app

# Create an ASGI app using the schema, running in debug mode
# Set context with authenticated graphql client.
#ontext_value={'client': getClient()}
app = GraphQL(
    schema, debug=True)

# 'Lifespan' is a standalone ASGI app.
# It implements the lifespan protocol,
# and allows registering lifespan event handlers.
lifespan = Lifespan()


@lifespan.on_event("startup")
async def startup():
    print("Starting up...")
    print("... done!")


@lifespan.on_event("shutdown")
async def shutdown():
    print("Shutting down...")
    print("... done!")

# 'LifespanMiddleware' returns an ASGI app.
# It forwards lifespan requests to 'lifespan',
# and anything else goes to 'app'.
app = LifespanMiddleware(app, lifespan=lifespan)
