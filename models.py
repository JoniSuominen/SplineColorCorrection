from sklearn.base import BaseEstimator, TransformerMixin, RegressorMixin 
from colour import polynomial_expansion, XYZ_to_Lab, apply_matrix_colour_correction
from colour.characterisation import polynomial_expansion_Finlayson2015
from sklearn.preprocessing import SplineTransformer
import numpy as np
from scipy.optimize import minimize
from colour_math import deltae_stats_nm
from pygam import LinearGAM, te, GammaGAM
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import cm


class PolynomialTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, degree=2, rp=True, method="Finlayson 2015"):
        self.degree = degree
        self.rp = rp
        self.method = method

    def fit(self, X, y=None):
        # Determine the knot locations based on the training data
        return self

    def transform(self, X):
        # Create the cubic spline terms using the knot locations
        return polynomial_expansion(X, method=self.method, degree=self.degree, root_polynomial_expansion=self.rp)


class TensorBSplineTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, degree, n_splines):
        self.n_splines = n_splines
        n_knots = n_splines - degree + 1
        self.degree = degree
        self.n_knots = n_knots
        knots_double = np.tile(np.linspace(0, 1, 2*n_knots).reshape(-1, 1), (1, 3))
        knots = np.tile(np.linspace(0, 1, n_knots).reshape(-1, 1), (1, 3))
        self.cubic_transformer = SplineTransformer(degree=self.degree, knots=knots)
        self.linear_transformer = SplineTransformer(degree=1, knots=knots)
        self.knot_interval = None
        
    def fit(self, X, y=None):


        self.cubic_transformer.fit(X)
        self.linear_transformer.fit(X)
        return self
        

    def _plot_basis_functions(self):
        # Generate sample points
        x = np.linspace(0, 1, 500).reshape(-1, 1)
        X_sample = np.tile(x, (1, 3))

        # Evaluate basis functions
        cubic_spline_basis = self.cubic_transformer.transform(X_sample)
        linear_spline_basis = self.linear_transformer.transform(X_sample)

        # Plot cubic basis functions
        plt.figure(figsize=(12, 6))
        for i in range(cubic_spline_basis.shape[1]):
            plt.plot(x, cubic_spline_basis[:, i], label=f'Cubic Spline {i+1}')
        plt.title('Cubic Basis Functions')
        plt.xlabel('X')
        plt.ylabel('Basis Function Value')
        plt.legend()
        plt.show(block=True)

        # Plot linear basis functions
        plt.figure(figsize=(12, 6))
        for i in range(linear_spline_basis.shape[1]):
            plt.plot(x, linear_spline_basis[:, i], label=f'Linear Spline {i+1}')
        plt.title('Linear Basis Functions')
        plt.xlabel('X')
        plt.ylabel('Basis Function Value')
        plt.legend()
        plt.show(block=True) 
    
    
class DeltaEOptimizer(BaseEstimator, RegressorMixin):
    def __init__(self, solver="BFGS", root_polynomial=True, degree=3):
        self.ccm = None
        self.solver = solver
        self.degree = degree
        self.root_polynomial = root_polynomial
        
        
    def fit(self, X, y=None):
        feature = polynomial_expansion_Finlayson2015(X[0, :], self.degree, self.root_polynomial)
        n_terms = feature.shape[0]
        self.coefs = np.ones((3 *  n_terms))
        result = minimize(deltae_stats_nm, self.coefs, method=self.solver, args=(X, XYZ_to_Lab(y), self.degree, self.root_polynomial, n_terms))

        print(result)
        self.ccm = result.x.reshape((3, n_terms))
        return self
        
    def predict(self, X):
        return apply_matrix_colour_correction(
            X,
            self.ccm,
            method="Finlayson 2015",
            degree=self.degree,
            root_polynomial_expansion=self.root_polynomial,
        )
    
class GAMOptimizer(BaseEstimator, RegressorMixin):
    def __init__(self, lams, order, n_splines=10, penalties="derivative"):
        self.lams = lams
        self.order = order
        self.n_splines = n_splines
        self.penalties = penalties
        self.predictor_X = None
        self.predictor_Y = None
        self.predictor_Z = None
        
        
    def fit(self, X, y=None):
        #a = s(1, 20,2)
        #a.compile(X)
        #tee = a.build_columns(X)
        term_rg = te(0,1, spline_order=self.order, n_splines=self.n_splines, penalties=self.penalties, edge_knots=[[0, 1], [0, 1]])
        term_rb = te(0,2, spline_order=self.order, n_splines=self.n_splines, penalties=self.penalties, edge_knots=[[0, 1], [0, 1]])
        term_gb = te(1,2, spline_order=self.order, n_splines=self.n_splines, penalties=self.penalties, edge_knots=[[0, 1], [0, 1]])
        interactions = term_rg + term_rb + term_gb

        self.predictor_X = LinearGAM(terms=interactions, lam=self.lams, fit_intercept=False)
        self.predictor_Y = LinearGAM(terms=interactions, lam=self.lams, fit_intercept=False)
        self.predictor_Z = LinearGAM(terms=interactions, lam=self.lams, fit_intercept=False)
        
        #self.predictor_X = LinearGAM(terms=s(0,spline_order=5) +s(1,spline_order=5) + s(2,spline_order=5) + s(0,spline_order=3, n_splines=40) + s(1,spline_order=3, n_splines=40) + s(2,spline_order=3, n_splines=40) + te(0,1,2, spline_order=5), lam=self.lams)
        #self.predictor_Y = LinearGAM(terms=s(0,spline_order=5) +s(1,spline_order=5) + s(2,spline_order=5) + s(0,spline_order=3, n_splines=40) + s(1,spline_order=3, n_splines=40) + s(2,spline_order=3, n_splines=40) + te(0,1,2, spline_order=5), lam=self.lams)
        #self.predictor_Z = LinearGAM(terms=s(0,spline_order=5) +s(1,spline_order=5) + s(2,spline_order=5) + s(0,spline_order=3, n_splines=40) + s(1,spline_order=3, n_splines=40) + s(2,spline_order=3, n_splines=40) + te(0,1,2, spline_order=5), lam=self.lams)
        self.predictor_X.fit(X, y[:, 0])
        self.predictor_Y.fit(X, y[:, 1])
        self.predictor_Z.fit(X, y[:, 2])

        print(3* self.predictor_X.coef_.shape[0])


        return self
    
    def plot_partial_dependences(self):
        n_features = self.predictor_X.statistics_['m_features']
        terms = {
            0: ['R', 'G'],
            1: ['R', 'B'],
            2: ['G', 'B']
        }
        for i, term in enumerate(self.predictor_X.terms):
            fig = plt.figure()
            x = terms[i][0]
            y = terms[i][1]
            pos1 = i*3 + 1
            pos2 = i*3 + 2
            pos3 = i*3 + 3
            # Create subplots
            ax1 = fig.add_subplot(1, 3, 1, projection='3d')
            ax2 = fig.add_subplot(1, 3, 2, projection='3d')
            ax3 = fig.add_subplot(1, 3, 3, projection='3d')
            XX = self.predictor_Y.generate_X_grid(term=i, meshgrid=True)
            X = self.predictor_X.partial_dependence(term=i, X=XX, meshgrid=True)
            Y = self.predictor_Y.partial_dependence(term=i, X=XX, meshgrid=True)
            Z = self.predictor_Z.partial_dependence(term=i, X=XX, meshgrid=True)
            ax1.plot_surface(XX[0], XX[1], X, cmap='viridis')
            ax2.plot_surface(XX[0], XX[1], Y, cmap='viridis')
            ax3.plot_surface(XX[0], XX[1], Z, cmap='viridis')
            XX2  = self.predictor_Y.generate_X_grid(term=i, meshgrid=True, n=self.n_splines)
            X2 = self.predictor_X.partial_dependence(term=i, X=XX2, meshgrid=True)
            Y2 = self.predictor_Y.partial_dependence(term=i, X=XX2, meshgrid=True)
            Z2 = self.predictor_Z.partial_dependence(term=i, X=XX2, meshgrid=True)
            ax1.scatter(XX2[0], XX2[1], X2,color='red', s=5)
            ax2.scatter(XX2[0], XX2[1], Y2,color='red', s=5)
            ax3.scatter(XX2[0], XX2[1], Z2,color='red', s=5)
            ax1.set_xlabel(x)
            ax1.set_ylabel(y)
            ax2.set_xlabel(x)
            ax2.set_ylabel(y)
            ax3.set_xlabel(x)
            ax3.set_ylabel(y)
            ax3.set_ylabel(y)
            ax1.set_title(f"Partial dependence of term {x+y} on X")
            ax2.set_title(f"Partial dependence of term {x+y} on Y")
            ax3.set_title(f"Partial dependence of term {x+y} on Z")
            fig.tight_layout(pad=1.0)        
            
    def plot_partial_dependences_for_Y(self):
        n_features = self.predictor_X.statistics_['m_features']
        terms = {
            0: ['R', 'G'],
            1: ['R', 'B'],
            2: ['G', 'B']
        }
        fig = plt.figure()
        gs = gridspec.GridSpec(2, 2)
        # Create subplots
        ax1 = fig.add_subplot(gs[0,0], projection='3d')
        ax2 = fig.add_subplot(gs[0,1], projection='3d')
        ax3 = fig.add_subplot(gs[1, :], projection='3d')
        XX = self.predictor_Y.generate_X_grid(term=0, meshgrid=True)
        Ysurf1 = self.predictor_Y.partial_dependence(term=0, X=XX, meshgrid=True)
        Ysurf2 = self.predictor_Y.partial_dependence(term=1, X=XX, meshgrid=True)
        Ysurf3 = self.predictor_Y.partial_dependence(term=2, X=XX, meshgrid=True)
        ax1.plot_surface(XX[0], XX[1], Ysurf1, cmap='viridis')
        ax2.plot_surface(XX[0], XX[1], Ysurf2, cmap='viridis')
        ax3.plot_surface(XX[0], XX[1], Ysurf3, cmap='viridis')
        XX2  = self.predictor_Y.generate_X_grid(term=0, meshgrid=True, n=self.n_splines)
        X2 = self.predictor_Y.partial_dependence(term=0, X=XX2, meshgrid=True)
        Y2 = self.predictor_Y.partial_dependence(term=1, X=XX2, meshgrid=True)
        Z2 = self.predictor_Y.partial_dependence(term=2, X=XX2, meshgrid=True)
        ax1.scatter(XX2[0], XX2[1], X2,color='red', s=5)
        ax2.scatter(XX2[0], XX2[1], Y2,color='red', s=5)
        ax3.scatter(XX2[0], XX2[1], Z2,color='red', s=5)
        ax1.set_xlabel("R")
        ax1.set_ylabel("G")
        ax2.set_xlabel("R")
        ax2.set_ylabel("B")
        ax3.set_xlabel("G")
        ax3.set_ylabel("B")
        ax1.set_zlabel("Y")
        ax2.set_zlabel("Y")
        ax3.set_zlabel("Y")
        #ax1.view_init(azim=-130)
        #ax2.view_init(azim=-130)
        #ax3.view_init(azim=-130)
        ax1.set_title(f"Partial dependence of term R/G on Y")
        ax2.set_title(f"Partial dependence of term R/B on Y")
        ax3.set_title(f"Partial dependence of term G/B on Y")
        fig.tight_layout(pad=2.0)    
        
    def plot_4d(self):
        n_samples = 100

        # Generate artificial 3D training samples
        samples = np.random.uniform(low=0, high=1, size=(n_samples, 3))
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.view_init(45,60)
        
        print(np.ones((n_samples, n_samples)).shape)


        V = self.predictor_Y.predict(samples)
        scatter = ax.scatter(samples[:, 0], samples[:, 1], samples[:, 2], c=V, cmap='Oranges')
        print(np.max(V))
        print(np.min(V))
        fig.colorbar(scatter, ax=ax, label='Fourth Dimension')



        
    def predict(self, X):
        Xp = self.predictor_X.predict(X)
        Yp = self.predictor_Y.predict(X)
        Zp = self.predictor_Z.predict(X)
        
        return np.vstack((Xp,Yp,Zp)).T
        