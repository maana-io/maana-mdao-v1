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

@query.field("multiDisciplineProblem")
def resolve_multi_discipline_problem(*_,  independantVariables, group, constraints, objective):
    
    # build the problem
    prob = om.Problem()

    # add group to hold disciplines
    cycle = prob.model.add_subsystem(group['name'], om.Group(), promotes=['*'])

    # create the independant variables
    indeps = prob.model.add_subsystem('indeps', om.IndepVarComp())
    # provides initial values for independant variables
    for indep in independantVariables:
        indeps.add_output(indep['id'], indep['value'])


    for d in group['explicitDisciplines']:
        cycle.add_subsystem(d['component']['name'],  om.ExecComp(d['component']["equation"]),  promotes_inputs=d['promotesInputs'],
                            promotes_outputs=d['promotesOutputs'])
    
    # Nonlinear Block Gauss Seidel is a gradient free solver
    cycle.nonlinear_solver = om.NonlinearBlockGS()

    #'obj = x**2 + z1 + y1 + exp(-y2)'
    #z=np.array([0.0, 0.0]), x=0.0),
    prob.model.add_subsystem(objective['id'], om.ExecComp(objective['equation']), promotes=objective['promotes'])


    # add constraints
    for c in constraints:
        prob.model.add_subsystem(c['name'], om.ExecComp(c['equation']), promotes=c['promotes'])
    
    prob.setup()


    prob.run_model()


    #prob['y1'][0], prob['y2'][0], prob['obj'][0], prob['con1'][0], prob['con2'][0])
    
    results = []

    #get objective value
    results.append({'id': objective['id'], 'value': prob[objective['id']][0]})
    # gets the output values
    for ec in group['explicitDisciplines']:
        for o in ec['promotesOutputs']:
            results.append({'id': o, 'value': prob[o][0]})

    for c in constraints:
        results.append({'id': c['name'], 'value': prob[c['name']][0]})

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
